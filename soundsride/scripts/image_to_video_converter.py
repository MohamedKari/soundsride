import logging
from pathlib import Path
from typing import Union
from argparse import ArgumentParser

from PIL import Image
from fire import Fire
import av

# should be an FFMPEG command instead

class ImagesToVideoConverter():
    
    def __init__(self, 
                 image_folder_path: Union[str, Path], 
                 output_path: Union[str, Path]):

        image_folder_path = Path(image_folder_path)
        output_path = Path(output_path)

        self.image_folder_path = image_folder_path
        self.output_path = output_path
    
    def convert(self):
        logging.getLogger(__name__).info(
            "Saving images from directory at path %s to video at path %s...",
            self.image_folder_path,
            self.output_path)
        
        output = av.open(str(self.output_path), "w")
        fps = 10
        stream = output.add_stream("h264", fps)
        stream.bit_rate = 8_000_000

        # Get image list 
        jpgs = list(self.image_folder_path.glob("*.jpg"))
        image_paths = list(jpgs)

        image_paths = sorted(image_paths, key=lambda s: int(Path(s).stem))

        # Determine size using a sample image
        first_image_path = image_paths[0]
        with open(first_image_path, "rb") as sample_file: 
            first_image = Image.open(sample_file)
            stream.width, stream.height = first_image.size
        
        origin_timestamp = int(image_paths[0].stem)
        duration_in_ms = 1000 / fps

        last_image_path = first_image_path
        timestamp_rel_last_added = 0

        # Create video stream
        for image_path in image_paths[1:]:
            timestamp_abs = int(image_path.stem)
            timestamp_rel = timestamp_abs - origin_timestamp

            print(timestamp_rel_last_added, timestamp_rel)
            
            while timestamp_rel_last_added < timestamp_rel:
                packet = stream.encode(av.VideoFrame.from_image(Image.open(last_image_path)))
                output.mux(packet)
                print(".", end="", flush=True)
                timestamp_rel_last_added += duration_in_ms
            
            last_image_path = image_path

            print("", flush=True)

        logging.getLogger(__name__).debug("Flushing to disk...")
        packet = stream.encode(None)
        output.mux(packet)
        logging.getLogger(__name__).debug("Done saving %s", self.output_path)

        output.close()


def run(image_folder_path: str,):
    output_path = Path(image_folder_path + ".mp4")
    images_to_video_converter = ImagesToVideoConverter(
        image_folder_path,
        output_path
    )

    images_to_video_converter.convert()

if __name__ == "__main__":
    Fire(run)