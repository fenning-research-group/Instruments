import cv2
import os
from datetime import datetime
import threading
import sys
import cv2
from typing import Optional
from vimba import *
from vimba.vimba import Camera, Vimba, VimbaCameraError, VimbaFeatureError

root = "c:\\Users\\FRG-users\\Documents\\Data\\"
today = datetime.now()
path = root + 'x' + today.strftime('%Y%m%d')
if os.path.exists(path) == False:
	os.mkdir(path)

streaming_exp_time = 50000 # streaing exposure time in ms

######################### Save Images #########################

def capture(fname, exposure_t = 10000):# image cpture exposure time in µs

    with Vimba.get_instance () as vimba:
        cams = vimba.get_all_cameras ()
        with cams [0] as cam:
            
            cam.ExposureTimeAbs.set(exposure_t)

            frame = cam.get_frame (2000)
            cv2.imwrite(os.path.join(path,f'{fname}.jpg'), frame.as_opencv_image())

			#frame.as_opencv_image () gives the np array


######################## Live Streaming ########################

# def preview():
#     run asynchronous_grab_opencv_zjd.py
#     #C:\Users\FRG-user\Documents\GitHub\VimbaPython\Examples\asynchronous_grab_opencv_zjd.py
def print_preamble():
    print('///////////////////////////////////////////////////////')
    print('/// Vimba API Asynchronous Grab with OpenCV Example ///')
    print('///////////////////////////////////////////////////////\n')


def print_usage():
    print('Usage:')
    print('    python asynchronous_grab_opencv.py [camera_id]')
    print('    python asynchronous_grab_opencv.py [/h] [-h]')
    print()
    print('Parameters:')
    print('    camera_id   ID of the camera to use (using first camera if not specified)')
    print()


def abort(reason: str, return_code: int = 1, usage: bool = False):
    print(reason + '\n')

    if usage:
        print_usage()

    sys.exit(return_code)


def parse_args() -> Optional[str]:
    args = sys.argv[1:]
    argc = len(args)

    for arg in args:
        if arg in ('/h', '-h'):
            print_usage()
            sys.exit(0)

    if argc > 1:
        abort(reason="Invalid number of arguments. Abort.", return_code=2, usage=True)

    return None if argc == 0 else args[0]


def get_camera(camera_id: Optional[str]) -> Camera:
    with Vimba.get_instance() as vimba:
        if camera_id:
            try:
                return vimba.get_camera_by_id(camera_id)

            except VimbaCameraError:
                abort('Failed to access Camera \'{}\'. Abort.'.format(camera_id))

        else:
            cams = vimba.get_all_cameras()
            if not cams:
                abort('No Cameras accessible. Abort.')

            return cams[0]


def setup_camera(cam: Camera, exposure_time = streaming_exp_time):#exposure time in ms
    with cam:

        try: 
            cam.ExposureTimeAbs.set(exposure_time) #modified by ZJD 20230414 to enable streaming exposure time change

        # Enable auto exposure time setting if camera supports it
        #try:
        #    cam.ExposureAuto.set('Continuous')

        except (AttributeError, VimbaFeatureError):
            pass

        # Enable white balancing if camera supports it
        try:
            cam.BalanceWhiteAuto.set('Continuous')

        except (AttributeError, VimbaFeatureError):
            pass

        # Try to adjust GeV packet size. This Feature is only available for GigE - Cameras.
        try:
            cam.GVSPAdjustPacketSize.run()

            while not cam.GVSPAdjustPacketSize.is_done():
                pass

        except (AttributeError, VimbaFeatureError):
            pass

        # Query available, open_cv compatible pixel formats
        # prefer color formats over monochrome formats
        cv_fmts = intersect_pixel_formats(cam.get_pixel_formats(), OPENCV_PIXEL_FORMATS)
        color_fmts = intersect_pixel_formats(cv_fmts, COLOR_PIXEL_FORMATS)

        if color_fmts:
            cam.set_pixel_format(color_fmts[0])

        else:
            mono_fmts = intersect_pixel_formats(cv_fmts, MONO_PIXEL_FORMATS)

            if mono_fmts:
                cam.set_pixel_format(mono_fmts[0])

            else:
                abort('Camera does not support a OpenCV compatible format natively. Abort.')


class Handler:
    def __init__(self):
        self.shutdown_event = threading.Event()

    def __call__(self, cam: Camera, frame: Frame):
        ENTER_KEY_CODE = 13

        key = cv2.waitKey(1)
        if key == ENTER_KEY_CODE:
            self.shutdown_event.set()
            cv2.destroyAllWindows()# added by ZJD to allow multiple opencv window pop-up in one kernel 2023/04/05
            return

        elif frame.get_status() == FrameStatus.Complete:
            print('{} acquired {}'.format(cam, frame), flush=True)

            msg = 'Stream from \'{}\'. Press <Enter> to stop stream.'
            cv2.imshow(msg.format(cam.get_name()), frame.as_opencv_image())

        cam.queue_frame(frame)


def streaming(exposure_time = streaming_exp_time):#untested change exp time function as of 09/03/2023, just used for live streaming, it works.
    print_preamble()
    cam_id = parse_args()

    with Vimba.get_instance():
        with get_camera(cam_id) as cam:

            setup_camera(cam, exposure_time = exposure_time)

            handler = Handler()

            try:
                # Start Streaming with a custom a buffer of 10 Frames (defaults to 5)
                cam.start_streaming(handler=handler, buffer_count=10)
                handler.shutdown_event.wait()

            finally:
                cam.stop_streaming()