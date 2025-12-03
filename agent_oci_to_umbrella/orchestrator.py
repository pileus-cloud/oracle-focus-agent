"""
Transfer orchestrator - coordinates file discovery and transfer.
"""

import os
import io
import time
from typing import List, Dict
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from .logger import get_logger


logger = get_logger("orchestrator")


class FileInfo:
    """Information about a file to transfer."""

    def __init__(self, oci_object_name: str, s3_key: str, size: int, time_created: datetime):
        self.oci_object_name = oci_object_name
        self.s3_key = s3_key
        self.size = size
        self.time_created = time_created

    def __repr__(self):
        return f"FileInfo(s3_key={self.s3_key}, size={self.size})"


class TransferStats:
    """Statistics for a transfer operation."""

    def __init__(self):
        self.files_discovered = 0
        self.files_transferred = 0
        self.files_skipped = 0
        self.files_failed = 0
        self.bytes_transferred = 0
        self.duration_seconds = 0.0
        self.errors: List[str] = []

    def __repr__(self):
        return (f"TransferStats(discovered={self.files_discovered}, "
                f"transferred={self.files_transferred}, skipped={self.files_skipped}, "
                f"failed={self.files_failed}, bytes={self.bytes_transferred})")


class TransferOrchestrator:
    """Orchestrates file discovery, filtering, and transfer."""

    def __init__(self, config, oci_client, s3_client, state_manager):
        """
        Initialize orchestrator.

        Args:
            config: Configuration object
            oci_client: OCI client instance
            s3_client: S3 client instance
            state_manager: State manager instance
        """
        self.config = config
        self.oci_client = oci_client
        self.s3_client = s3_client
        self.state_manager = state_manager

    def sync(self, force: bool = False) -> TransferStats:
        """
        Perform a complete sync operation.

        Args:
            force: If True, re-transfer all files ignoring state

        Returns:
            TransferStats with results
        """
        start_time = time.time()
        stats = TransferStats()

        logger.info("=" * 70)
        if force:
            logger.info("Starting sync operation (FORCED - ignoring state)")
        else:
            logger.info("Starting sync operation")
        logger.info("=" * 70)

        try:
            # Calculate date range
            dates = self._calculate_date_range()
            logger.info(f"Processing date range: {dates[0]} to {dates[-1]} ({len(dates)} days)")

            # Discover files
            all_files = []
            for date_obj in dates:
                files = self._discover_files_for_date(date_obj)
                all_files.extend(files)

            stats.files_discovered = len(all_files)
            logger.info(f"Discovered {stats.files_discovered} total files")

            if not all_files:
                logger.info("No files to transfer")
                stats.duration_seconds = time.time() - start_time
                return stats

            # Filter files (check state unless forced)
            files_to_transfer = self._filter_files(all_files, force=force)
            stats.files_skipped = stats.files_discovered - len(files_to_transfer)

            logger.info(f"Files to transfer: {len(files_to_transfer)}")
            if force:
                logger.info(f"Files skipped: {stats.files_skipped} (force mode: re-transferring all)")
            else:
                logger.info(f"Files skipped (already transferred): {stats.files_skipped}")

            if not files_to_transfer:
                logger.info("All files already transferred")
                stats.duration_seconds = time.time() - start_time
                return stats

            # Transfer files
            transfer_results = self._transfer_files(files_to_transfer)

            stats.files_transferred = transfer_results["succeeded"]
            stats.files_failed = transfer_results["failed"]
            stats.bytes_transferred = transfer_results["bytes_transferred"]
            stats.errors = transfer_results["errors"]

            # Cleanup old state records
            self.state_manager.cleanup_old_records()

        except Exception as e:
            logger.error(f"Sync operation failed: {e}", exc_info=True)
            stats.errors.append(str(e))

        stats.duration_seconds = time.time() - start_time

        # Log summary
        logger.info("=" * 70)
        logger.info("Sync operation complete")
        logger.info(f"  Discovered: {stats.files_discovered}")
        logger.info(f"  Transferred: {stats.files_transferred}")
        logger.info(f"  Skipped: {stats.files_skipped}")
        logger.info(f"  Failed: {stats.files_failed}")
        logger.info(f"  Data transferred: {self._format_size(stats.bytes_transferred)}")
        logger.info(f"  Duration: {stats.duration_seconds:.1f}s")
        logger.info("=" * 70)

        return stats

    def _calculate_date_range(self) -> List[date]:
        """Calculate date range to process based on lookback_days."""
        today = datetime.now().date()
        dates = []

        for i in range(self.config.agent.lookback_days, -1, -1):
            dates.append(today - timedelta(days=i))

        return dates

    def _discover_files_for_date(self, date_obj: date) -> List[FileInfo]:
        """
        Discover files from OCI for a specific date.

        Args:
            date_obj: Date to discover files for

        Returns:
            List of FileInfo objects
        """
        # Construct OCI prefix: "FOCUS Reports/2024/11/28/"
        prefix = f"{self.config.oci.prefix}{date_obj.year}/{date_obj.month:02d}/{date_obj.day:02d}/"

        logger.info(f"Discovering files for {date_obj} (prefix: {prefix})")

        try:
            oci_objects = self.oci_client.list_objects(prefix)

            files = []
            for obj in oci_objects:
                # Validate file size if enabled
                if self.config.advanced.validate_file_size:
                    max_size_bytes = self.config.advanced.max_file_size_gb * 1024 * 1024 * 1024
                    if obj.size > max_size_bytes:
                        logger.warning(f"Skipping {obj.name}: size {obj.size} exceeds limit")
                        continue

                # Generate S3 key
                s3_key = self._generate_s3_key(obj.name, date_obj)

                files.append(FileInfo(
                    oci_object_name=obj.name,
                    s3_key=s3_key,
                    size=obj.size,
                    time_created=obj.time_created
                ))

            logger.info(f"Found {len(files)} files for {date_obj}")
            return files

        except Exception as e:
            logger.error(f"Failed to discover files for {date_obj}: {e}")
            return []

    def _generate_s3_key(self, oci_object_name: str, date_obj: date) -> str:
        """
        Generate S3 key from OCI object name with hierarchical date structure.

        Args:
            oci_object_name: Full OCI object name
            date_obj: Date for directory structure

        Returns:
            S3 key with hierarchical date path (YYYY/MM/DD/filename.csv.gz)
        """
        # Extract filename from OCI path
        basename = os.path.basename(oci_object_name)

        # Create hierarchical date structure: YYYY/MM/DD/
        year = date_obj.strftime("%Y")
        month = date_obj.strftime("%m")
        day = date_obj.strftime("%d")

        # Return hierarchical S3 key matching OCI structure
        return f"{year}/{month}/{day}/{basename}"

    def _filter_files(self, files: List[FileInfo], force: bool = False) -> List[FileInfo]:
        """
        Filter files based on state (skip already transferred).

        Args:
            files: List of all discovered files
            force: If True, return all files (ignore state)

        Returns:
            List of files that need to be transferred
        """
        # If force mode, transfer all files regardless of state
        if force:
            logger.info("Force mode enabled: transferring all files regardless of state")
            return files

        files_to_transfer = []

        for file_info in files:
            if not self.state_manager.is_transferred(
                file_info.s3_key,
                file_info.size,
                file_info.time_created
            ):
                files_to_transfer.append(file_info)
            else:
                logger.debug(f"Skipping {file_info.s3_key} (already transferred)")

        return files_to_transfer

    def _transfer_files(self, files: List[FileInfo]) -> Dict:
        """
        Transfer multiple files in parallel.

        Args:
            files: List of files to transfer

        Returns:
            Dictionary with transfer results
        """
        max_workers = self.config.agent.max_concurrent_transfers
        succeeded = 0
        failed = 0
        bytes_transferred = 0
        errors = []

        logger.info(f"Starting parallel transfers (max {max_workers} concurrent)")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all transfers
            future_to_file = {
                executor.submit(self._transfer_single_file, file_info): file_info
                for file_info in files
            }

            # Process results as they complete
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                try:
                    result = future.result()
                    if result["success"]:
                        succeeded += 1
                        bytes_transferred += result["bytes_transferred"]
                        logger.info(f"✓ Transferred: {file_info.s3_key} ({self._format_size(file_info.size)})")
                    else:
                        failed += 1
                        error_msg = f"Failed to transfer {file_info.s3_key}: {result.get('error', 'Unknown error')}"
                        errors.append(error_msg)
                        logger.error(f"✗ {error_msg}")

                except Exception as e:
                    failed += 1
                    error_msg = f"Exception transferring {file_info.s3_key}: {e}"
                    errors.append(error_msg)
                    logger.error(f"✗ {error_msg}")

        return {
            "succeeded": succeeded,
            "failed": failed,
            "bytes_transferred": bytes_transferred,
            "errors": errors,
        }

    def _transfer_single_file(self, file_info: FileInfo) -> Dict:
        """
        Transfer a single file from OCI to S3.

        Args:
            file_info: File to transfer

        Returns:
            Dictionary with transfer result
        """
        start_time = time.time()

        try:
            logger.debug(f"Starting transfer: {file_info.oci_object_name} -> {file_info.s3_key}")

            # Create an in-memory buffer for streaming
            buffer = io.BytesIO()

            # Download from OCI to buffer
            bytes_downloaded = self.oci_client.download_stream(file_info.oci_object_name, buffer)

            # Reset buffer position for upload
            buffer.seek(0)

            # Upload from buffer to S3
            self.s3_client.upload_stream(file_info.s3_key, buffer, file_info.size)

            duration = time.time() - start_time

            # Mark as transferred in state
            self.state_manager.mark_transferred(
                oci_object_name=file_info.oci_object_name,
                s3_key=file_info.s3_key,
                size=file_info.size,
                time_created=file_info.time_created,
                duration_seconds=duration
            )

            return {
                "success": True,
                "bytes_transferred": bytes_downloaded,
                "duration_seconds": duration,
            }

        except Exception as e:
            logger.error(f"Transfer failed for {file_info.s3_key}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format size in bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
