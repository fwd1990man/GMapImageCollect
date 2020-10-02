"""Take huge detailed screenshots of Google Maps."""

from datetime import datetime
import os
import time
import tkinter

from PIL import Image
import pyscreenshot
from selenium import webdriver
# import chromedriver_binary


def create_map(lat_start: float, long_start: float,
               number_rows: int, number_cols: int,
               scale: float=1, sleep_time: float=0,
               offset_left: float=0, offset_top: float=0,
               offset_right: float=0, offset_bottom: float=0,
               outfile: str=None):
    """Create a big Google Map image from a grid of screenshots.

    ARGS:
        lat_start: Top-left coodinate to start taking screenshots.
        long_start: Top-left coodinate to start taking screenshots.
        number_rows: Number of screenshots to take for map.
        number_cols: Number of screenshots to take for map.
        scale: Percent to scale each image to reduce final resolution
            and filesize. Should be a float value between 0 and 1.
            Recommend to leave at 1 for production, and between 0.05
            and 0.2 for testing.
        sleep_time: Seconds to sleep between screenshots.
            Needed because Gmaps has some AJAX queries that will make
            the image better a few seconds after confirming page load.
            Recommend 0 for testing, and 3-5 seconds for production.
        offset_*: Percent of each side to crop from screenshots.
            Each should be a float value between 0 and 1. Offsets should
            account for all unwanted screen elements, including:
            taskbars, windows, multiple displays, and Gmaps UI (minimap,
            search box, compass/zoom buttons). Defaults are set for an
            Ubuntu laptop with left-side taskbar, and will need to be
            tuned to the specific machine and setup where it will be run.
        outfile: If provided, the program will save the final image to
            this filepath. Otherwise, it will be saved in the current
            working directory with name 'testimg-<timestamp>.png'
    """
    if outfile:
        # Make sure the path doesn't exist, is writable, and is a .PNG
        assert not os.path.exists(outfile)
        assert os.access(os.path.dirname(os.path.abspath(outfile)), os.W_OK)
        assert outfile.upper().endswith('.PNG')

    # driver = webdriver.Firefox()
    driver = webdriver.Chrome()
    driver.maximize_window()
    # 2D grid of Images to be stitched together
    images = [[None for _ in range(number_cols)]
              for _ in range(number_rows)]

    # Calculate amount to shift lat/long each screenshot
    screen_width, screen_height = get_screen_resolution()
    lat_shift = calc_latitude_shift(screen_height,
                                    (offset_top + offset_bottom))
    long_shift = calc_longitude_shift(screen_width,
                                      (offset_left + offset_right))

    for row in range(number_rows):
        for col in range(number_cols):
            latitude = lat_start + (lat_shift * row)
            longitude = long_start + (long_shift * col)
            # Show the map using the Firefox driver
            # ,678m/data=!3m1!1e3
            # url = (
            #     'https://www.google.com/maps/@{lat},{long},589m/data=!3m1!1e3'
            #     ).format(lat=latitude, long=longitude)
            # url = (
            #     'https://www.google.com/maps/@{lat},{long},678m/data=!3m1!1e3'
            #     ).format(lat=latitude, long=longitude)
            #,467m/data=!3m1!1e3
            # url = (
            #     'https://www.google.com/maps/@{lat},{long},18z'
            #     ).format(lat=latitude, long=longitude)
            # url = (
            #     'https://www.google.com/maps/@{lat},{long},467m/data=!3m1!1e3'
            #     ).format(lat=latitude, long=longitude)
            url = (
                'https://www.google.com/maps/@{lat},{long},18z/data=!3m1!1e3'
                ).format(lat=latitude, long=longitude)
            print(url)
            driver.get(url)
            # Let the map load all assets before taking a screenshot
            time.sleep(sleep_time)
            image = screenshot(screen_width, screen_height,
                               offset_left, offset_top,
                               offset_right, offset_bottom)
            # Scale image up or down if desired, then save in memory
            images[row][col] = scale_image(image, scale)

    driver.close()
    driver.quit()

    # Combine all the images into one, then save it to disk
    final = combine_images(images)
    if not outfile:
        timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
        outfile = 'testimg-{}.png'.format(timestamp)
    final.save(outfile)


def get_screen_resolution() -> tuple:
    """Return tuple of (width, height) of screen resolution in pixels."""
    root = tkinter.Tk()
    root.withdraw()
    return (root.winfo_screenwidth(), root.winfo_screenheight())


def calc_latitude_shift(screen_height: int, percent_hidden: float) -> float:
    """Return the amount to shift latitude per row of screenshots."""
    # return -0.000002051 * screen_height * (1 - percent_hidden)
    return -0.000002051 * screen_height * (1 - percent_hidden) * 2.1
    # return -0.00002051 * screen_height * (1 - percent_hidden)


def calc_longitude_shift(screen_width: int, percent_hidden: float) -> float:
    """Return the amount to shift longitude per column of screenshots."""
    return 0.00000268 * screen_width * (1 - percent_hidden) * 2
    # return 0.0000268 * screen_width * (1 - percent_hidden)


def screenshot(screen_width: int, screen_height: int,
               offset_left: float, offset_top: float,
               offset_right: float, offset_bottom: float) -> Image:
    """Return a screenshot of only the pure maps area."""
    x1 = offset_left * screen_width
    y1 = offset_top * screen_height
    x2 = (offset_right * -screen_width) + screen_width
    y2 = (offset_bottom * -screen_height) + screen_height
    # image = pyscreenshot.grab(bbox=(int(x1), int(y1), int(x2), int(y2)))
    image = pyscreenshot.grab(bbox=(int(x1), int(y1), int(x2), int(y2)))
    return image


def scale_image(image: Image, scale: float) -> Image:
    """Scale an Image by a proportion, maintaining aspect ratio."""
    width = round(image.width * scale)
    height = round(image.height * scale)
    image.thumbnail((width, height))
    return image


def combine_images(images: list) -> Image:
    """Return combined image from a grid of identically-sized images.

    images is a 2d list of Image objects. The images should
    be already sorted/arranged when provided to this function.
    """
    imgwidth = images[0][0].width
    imgheight = images[0][0].height
    newsize = (imgwidth * len(images[0]), imgheight * len(images))
    newimage = Image.new('RGB', newsize)

    # Add all the images from the grid to the new, blank image
    for rowindex, row in enumerate(images):
        for colindex, image in enumerate(row):
            location = (colindex * imgwidth, rowindex * imgheight)
            newimage.paste(image, location)

    return newimage
