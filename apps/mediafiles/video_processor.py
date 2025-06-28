import os
import tempfile
import ffmpeg
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError


class VideoProcessor:
    """
    Server-side video processing for universal mobile compatibility.
    """

    @staticmethod
    def convert_to_h264(input_path: str, output_path: str) -> dict:
        """
        Convert video to H.264/MP4 for universal mobile compatibility.

        Args:
            input_path: Path to input video file
            output_path: Path for output video file

        Returns:
            dict: Conversion results with metadata
        """
        try:
            # Probe input file
            probe = ffmpeg.probe(input_path)
            video_stream = next((stream for stream in probe['streams']
                               if stream['codec_type'] == 'video'), None)

            if not video_stream:
                raise ValidationError("No video stream found")

            # Check duration limit
            duration = float(video_stream.get('duration', 0))
            max_duration = getattr(settings, 'MEDIA_VIDEO_MAX_DURATION', 120)
            if duration > max_duration:
                raise ValidationError(f"Video too long: {duration}s > {max_duration}s")

            # Convert to H.264/MP4 with mobile-optimized settings
            (
                ffmpeg
                .input(input_path)
                .output(
                    output_path,
                    vcodec='libx264',
                    acodec='aac',
                    preset='medium',
                    crf=23,  # Good quality for medical content
                    movflags='+faststart',  # Web optimization
                    pix_fmt='yuv420p',  # Universal compatibility
                    vf='scale=trunc(iw/2)*2:trunc(ih/2)*2'  # Ensure even dimensions
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Get output file info
            output_probe = ffmpeg.probe(output_path)
            output_video = next((stream for stream in output_probe['streams']
                               if stream['codec_type'] == 'video'), None)

            return {
                'success': True,
                'original_size': os.path.getsize(input_path),
                'converted_size': os.path.getsize(output_path),
                'duration': duration,
                'width': int(output_video.get('width', 0)),
                'height': int(output_video.get('height', 0)),
                'codec': output_video.get('codec_name', 'h264')
            }

        except Exception as e:
            raise ValidationError(f"Video conversion failed: {str(e)}")

    @staticmethod
    def generate_thumbnail(video_path: str, thumbnail_path: str, time_offset: float = 1.0):
        """
        Generate thumbnail from video at specified time offset.
        """
        try:
            (
                ffmpeg
                .input(video_path, ss=time_offset)
                .output(
                    thumbnail_path,
                    vframes=1,
                    format='image2',
                    vcodec='mjpeg',
                    **{'q:v': 2, 's': '300x300'}
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return True
        except Exception:
            return False