import os
import sys
import re
import multiprocessing
if getattr(sys, 'frozen', False):
    multiprocessing.freeze_support()  # for PyInstaller support
import configparser
from threading import Event
from threading import Lock
from tkinter import Tk     # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askdirectory
import dearpygui.dearpygui as dpg
from Sequence_Converter import SequenceConverter
from Sequence_Converter import SequenceConverterSettings

class ConverterUI:

    #UI IDs for the DearPyGUI
    text_input_Dir_ID = 0
    text_output_Dir_ID = 0
    text_error_log_ID = 0
    text_info_log_ID = 0
    progress_bar_ID = 0
    thread_count_ID = 0
    srgb_check_ID = 0
    pointcloud_decimation_ID = 0
    decimation_percentage_ID = 0
    save_normals_ID = 0
    generate_normals_ID = 0

    ### +++++++++++++++++++++++++  PACKAGE INTO SINGLE EXECUTABLE ++++++++++++++++++++++++++++++++++
    #Use this prompt in the terminal to package this script into a single executable for your system
    #You need to have PyInstaller installed in your local environment
    # pyinstaller Sequence_Converter_UI.py --collect-all=pymeshlab --collect-all=numpy --icon=resources/logo.ico -F
    ### +++++++++++++++++++++++++  PACKAGE INTO SINGLE MACOS APP  ++++++++++++++++++++++++++++++++++
    # pyinstaller Sequence_Converter_UI.py --icon=resources/logo.icns --windowed --strip

    isRunning = False
    conversionFinished = False
    inputPathValid = False
    outputPathValid = False
    processedFileCount = 0
    totalFileCount = 0

    applicationPath = ""
    configPath = ""
    resourcesPath = ""
    noPathWarning = "[No folder set]"
    inputSequencePath = noPathWarning
    outputSequencePath = noPathWarning
    proposedOutputPath = ""

    modelPathList = []
    imagePathList = []
    generateDDS = True
    generateASTC = True
    convertToSRGB = False
    decimatePointcloud = False
    generateNormals = False
    save_normals = False
    decimatePercentage = 100
    mergePoints = False
    mergeDistance = 0.001

    validModelTypes = ["obj", "3ds", "fbx", "glb", "gltf", "obj", "ply", "ptx", "stl", "xyz", "pts"]
    validImageTypes = ["jpg", "jpeg", "png", "bmp", "tga"]
    invalidImageTypes = ["dds", "atsc"]

    converter = SequenceConverter()
    terminationSignal = Event()
    progressbarLock = Lock()


    # --- UI Callbacks ---
    def open_input_dir_cb(self):
        selectedDir = self.open_file_dialog(self.inputSequencePath)
        self.set_input_files(selectedDir)

    def open_output_dir_cb(self):
        if(self.outputSequencePath is None or len(self.outputSequencePath) < 1):
            selectedDir = self.open_file_dialog(self.inputSequencePath)
        else:
            selectedDir = self.open_file_dialog(self.outputSequencePath)

        self.set_output_files(selectedDir)

    def cancel_processing_cb(self):
        self.terminationSignal.set()
        self.converter.terminate_conversion()

    def set_DDS_enabled_cb(self, sender, app_data):
        self.generateDDS = app_data
        self.write_config_bool("DDS", app_data)

    def set_ASTC_enabled_cb(self, sender, app_data):
        self.generateASTC = app_data
        self.write_config_bool("ASTC", app_data)

    def set_SRGB_enabled_cb(self, sender, app_data):
        self.convertToSRGB = app_data

    def set_Decimation_enabled_cb(self, sender, app_data):
        self.decimatePointcloud = app_data
        self.write_config_bool("decimatePointcloud", app_data)

    def set_Decimation_percentage_cb(self, sender, app_data):
        self.decimatePercentage = app_data
        self.write_settings_string("decimatePercentage", str(app_data))

    def set_Generate_Normals_enabled_cb(self, sender, app_data):
        self.generateNormals = app_data
        self.save_normals = app_data
        dpg.set_value(self.save_normals_ID, app_data)
        self.write_settings_string("generateNormals", str(app_data))

    def set_normals_enabled_cb(self, sender, app_data):
        self.save_normals = app_data
        self.write_settings_string("saveNormals", str(app_data))

    def set_Merge_Points_cb(self, sender, app_data):
        self.mergePoints = app_data
        self.write_settings_string("mergePoints", str(app_data))

    def set_Merge_Distance_cb(self, sender, app_data):
        self.mergeDistance = app_data
        self.write_settings_string("mergeDistance", str(app_data))

    def start_conversion_cb(self):

        if(self.isRunning):
            return

        self.terminationSignal.clear()

        self.info_text_clear()
        self.error_text_clear()

        if(self.inputPathValid == False):
            self.error_text_set("Input files are not configured correctly")
            return False

        if(self.outputPathValid == False and self.proposedOutputPath == "" ):
            self.error_text_set("Output folder is not configured correctly")
            return False

        if(self.outputPathValid == False and len(self.outputSequencePath) > 1 ):
            if not (os.path.exists(self.proposedOutputPath)):
                os.mkdir(self.proposedOutputPath)

        self.totalFileCount =  len(self.modelPathList)
        if(self.generateASTC or self.generateDDS):
            self.totalFileCount += len(self.imagePathList)
        self.processedFileCount = 0

        convertSettings = SequenceConverterSettings()
        convertSettings.modelPaths = self.modelPathList
        convertSettings.imagePaths = self.imagePathList
        convertSettings.inputPath = self.inputSequencePath
        convertSettings.outputPath = self.get_output_path()
        convertSettings.resourcePath = self.resourcesPath
        convertSettings.maxThreads = dpg.get_value(self.thread_count_ID)
        convertSettings.convertToDDS = self.generateDDS
        convertSettings.convertToASTC = self.generateASTC
        convertSettings.convertToSRGB = self.convertToSRGB
        convertSettings.decimatePointcloud = self.decimatePointcloud
        convertSettings.decimatePercentage = self.decimatePercentage
        convertSettings.saveNormals = self.save_normals
        convertSettings.generateNormals = self.generateNormals
        convertSettings.mergePoints = self.mergePoints
        convertSettings.mergeDistance = self.mergeDistance

        self.converter.start_conversion(convertSettings, self.single_conversion_finished_cb)

        self.info_text_set("Converting...")
        self.set_progressbar(0)
        self.isRunning = True


    def single_conversion_finished_cb(self, error, errorText):
        self.advance_progressbar(error, errorText)


    # --- File Handeling ---

    def InitDefaultPaths(self):

        # determine if application is a script file or frozen exe and get the executable path
        if getattr(sys, 'frozen', False):
            self.applicationPath = os.path.abspath(os.path.dirname(sys.executable))
        elif __file__:
            self.applicationPath = os.path.abspath(os.path.dirname(__file__))

        self.applicationPath += os.sep

        if (sys.platform == "darwin") and (getattr(sys, 'frozen', False)):
            self.resourcesPath = os.path.abspath(self.applicationPath + "../Resources/")
        else:
            self.resourcesPath = os.path.join(self.applicationPath, "resources") + os.sep

        self.configPath = os.path.join(self.resourcesPath, "config.ini")
        self.config = configparser.ConfigParser()

    def open_file_dialog(self, path):
        Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing

        if(path is None):
            new_input_path = askdirectory()
        else:
            new_input_path = askdirectory(initialdir=path, )

        return new_input_path

    def set_input_files(self, new_input_path):

        self.inputPathValid = False
        self.error_text_clear()
        self.imagePathList.clear()
        self.modelPathList.clear()

        res = self.validate_input_files(new_input_path)

        if(res == True):
            self.inputSequencePath = new_input_path
            self.input_path_label_set(new_input_path)
            self.info_text_set("Input files set!")

            # Propose an output dir
            self.set_proposed_output_files(new_input_path)

            self.inputPathValid = True
            self.write_path_string("input", new_input_path)

        else:
            self.info_text_clear()
            self.error_text_set(res)

    def validate_input_files(self, input_path):

            if(os.path.exists(input_path) == False):
                return "Folder does not exist!"

            files = os.listdir(input_path)

            #Sort the files into model and images
            for file in files:
                splitted_path = file.split(".")
                file_ending = splitted_path[len(splitted_path) - 1]

                if(file_ending in self.validModelTypes):
                    self.modelPathList.append(file)

                elif(file_ending in self.validImageTypes):
                    self.imagePathList.append(file)

                elif(file_ending in self.invalidImageTypes):
                    return "Can't convert already compressed (.dds, .astc) images! Please supply the images as .jpg, .png, .bmp or .tga!"

            if(len(self.modelPathList) < 1 and len(self.imagePathList) < 1):
                return "No model/image files found in folder!"

            if(len(self.imagePathList) > 1):
                self.convertToSRGB = self.converter.get_image_gamme_encoded(os.path.join(input_path, self.imagePathList[0]))
                self.set_SRGB_enabled(self.convertToSRGB)

            self.human_sort(self.modelPathList)
            self.human_sort(self.imagePathList)

            return True

    def set_proposed_output_files(self, input_path):

        if(len(self.outputSequencePath) < 1 or self.outputSequencePath == self.noPathWarning):
            self.proposedOutputPath = os.path.join(input_path, "converted")
            self.output_path_label_set("Proposed path: " + self.proposedOutputPath)

    def set_output_files(self, new_output_path):

        self.outputPathValid = False

        self.info_text_clear()
        self.error_text_clear()

        if(os.path.exists(new_output_path) == True):
            self.outputSequencePath = new_output_path
            self.output_path_label_set(new_output_path)
            self.info_text_set("Output folder set!")
            self.outputPathValid = True
            self.proposedOutputPath = ""

        else:
            self.info_text_clear()
            self.error_text_set("Error: Output directory is not valid!")

    def get_output_path(self):
        if(len(self.outputSequencePath) > 1 and self.proposedOutputPath == ""):
            return self.outputSequencePath
        else:
            return self.proposedOutputPath

    def load_config(self):
        #Create config on first startup
        if not (os.path.exists(self.configPath)):
            self.config['Paths'] = {}
            self.config['Settings'] = {}
            self.config['Paths']['input'] = ""
            self.config['Settings']['DDS'] = "true"
            self.config['Settings']['ASTC'] = "true"
            self.config['Settings']['decimatePointcloud'] = "false"
            self.config['Settings']['decimatePercentage'] = "100"
            self.config['Settings']['saveNormals'] = "false"
            self.config['Settings']['generateNormals'] = "false"
            self.config['Settings']['mergePoints'] = "false"
            self.config['Settings']['mergeDistance'] = "0.001"
            self.save_config()

        self.config.read(self.configPath)

    def read_path_string(self, key):
        return self.config['Paths'][key]

    def read_settings_string(self, key):
        return self.config['Settings'][key]

    def read_config_bool(self, key):
        return self.config['Settings'].getboolean(key)

    def write_path_string(self, key, value):
        self.config['Paths'][key] = value

    def write_settings_string(self, key, value):
        self.config['Settings'][key] = value

    def write_config_bool(self, key, value):
        self.config['Settings'][key] = str(value)

    def save_config(self):
        with open(self.configPath, "w") as configfile:
                self.config.write(configfile)

    def tryint(self, s):
        try:
            return int(s)
        except ValueError:
            return s

    def alphanum_key(self, s):
        return [ self.tryint(c) for c in re.split('([0-9]+)', s) ]

    def human_sort(self, l):
        l.sort(key=self.alphanum_key)


    # --- Main UI ---

    def advance_progressbar(self, error, errorText):

        self.progressbarLock.acquire()
        self.processedFileCount += 1

        if(error):
            self.error_text_set(errorText)
            self.cancel_processing_cb()
            self.set_progressbar(1)
            self.info_text_set("Error occurred during conversion: ")

        else:
            if(self.terminationSignal.is_set() == False):
                self.set_progressbar(self.processedFileCount / self.totalFileCount)
                self.info_text_set("Converting: " + str(self.processedFileCount) + " / " + str(self.totalFileCount))

            else:
                self.set_progressbar(0)
                self.info_text_set("Cancelling")

        if(self.processedFileCount == self.totalFileCount):
            self.conversionFinished = True
            print("Conversion finished")

        self.progressbarLock.release()

    def finish_conversion(self):
        self.converter.finish_conversion(not self.terminationSignal.is_set())

        if(self.terminationSignal.is_set()):
            self.info_text_set("Canceled!")
        else:
            self.info_text_set("Finished!")
        self.set_progressbar(0)

        self.isRunning = False

    def set_progressbar(self, progress):
        dpg.set_value(self.progress_bar_ID, progress)

    def info_text_set(self, info_text):
        dpg.set_value(self.text_info_log_ID, info_text)

    def info_text_clear(self):
        dpg.set_value(self.text_info_log_ID, "")

    def error_text_set(self, error_text):
        dpg.set_value(self.text_error_log_ID, error_text)

    def error_text_clear(self):
        dpg.set_value(self.text_error_log_ID, "")

    def input_path_label_set(self, input_path):
        dpg.set_value(self.text_input_Dir_ID, input_path)

    def output_path_label_set(self, output_path):
        dpg.set_value(self.text_output_Dir_ID, output_path)

    def set_SRGB_enabled(self, enabled):
        dpg.set_value(self.srgb_check_ID, enabled)

    def set_viewport_height(self, pointcloud_settings, texture_settings):
        default_viewport_height = 450
        pointcloud_settings_height = 70
        textures_settings_height = 70

        height = default_viewport_height
        if(pointcloud_settings):
            height += pointcloud_settings_height
        if(texture_settings):
            height += textures_settings_height

        dpg.set_viewport_height(height)


    def RunUI(self):

        dpg.create_context()

        self.InitDefaultPaths()
        self.config = configparser.ConfigParser()
        self.load_config()
        self.generateDDS = self.read_config_bool("DDS")
        self.generateASTC = self.read_config_bool("ASTC")
        self.decimatePointcloud = self.read_config_bool("decimatePointcloud")
        self.decimatePercentage = int(self.read_settings_string("decimatePercentage"))

        dpg.configure_app(manual_callback_management=True)
        dpg.create_viewport(height=500, width=500, title="Geometry Sequence Converter")
        dpg.setup_dearpygui()

        with dpg.window(label="Geometry Sequence Converter", tag="main_window", min_size= [500, 500]):

            dpg.add_button(label="Select Input Directory", callback=lambda:self.open_input_dir_cb())
            self.text_input_Dir_ID = dpg.add_text(self.inputSequencePath, wrap=450)

            dpg.add_spacer(height=40)

            dpg.add_button(label="Select Output Directory", callback=lambda:self.open_output_dir_cb())
            self.text_output_Dir_ID = dpg.add_text(self.outputSequencePath, wrap=450)

            dpg.add_spacer(height=30)

            dpg.add_text("General settings:")
            self.save_normals_ID = dpg.add_checkbox(label="Save normals", default_value=self.save_normals, callback=self.set_normals_enabled_cb)

            dpg.add_spacer(height=5)

            with dpg.collapsing_header(label="Pointcloud settings", default_open=False) as header_pcSettings_ID:

                with dpg.group(horizontal=True):
                    self.pointcloud_decimation_ID = dpg.add_checkbox(label="Decimate Pointcloud", default_value=self.decimatePointcloud, callback=self.set_Decimation_enabled_cb)
                    self.decimation_percentage_ID = dpg.add_input_int(label=" %", default_value=self.decimatePercentage, min_value=0, max_value=100, width=80, callback=self.set_Decimation_percentage_cb)

                with dpg.group(horizontal=True):
                    self.pointcloud_merge_ID = dpg.add_checkbox(label= "Merge Points by Distance: ", default_value=self.mergePoints, callback=self.set_Merge_Points_cb)
                    self.merge_distance_ID = dpg.add_input_float(label= " ", default_value=self.mergeDistance , callback=self.set_Merge_Distance_cb, min_value=0, width= 200)

                self.generate_normals_ID = dpg.add_checkbox(label= "Estimate normals", default_value=self.generateNormals, callback=self.set_Generate_Normals_enabled_cb)

            dpg.add_spacer(height=5)

            with dpg.collapsing_header(label="Texture settings", default_open=False) as header_textureSettings_ID:
                dpg.add_checkbox(label="Generate textures for desktop devices (DDS)", default_value=self.generateDDS, callback=self.set_DDS_enabled_cb)
                dpg.add_checkbox(label="Generate textures mobile devices (ASTC)", default_value=self.generateASTC, callback=self.set_ASTC_enabled_cb)
                self.srgb_check_ID = dpg.add_checkbox(label="Convert to SRGB profile", default_value=self.convertToSRGB, callback=self.set_SRGB_enabled_cb)

            self.text_error_log_ID = dpg.add_text("", color=[255, 0, 0], wrap=450)
            self.text_info_log_ID = dpg.add_text("", color=[255, 255, 255], wrap=450)

            self.progress_bar_ID = dpg.add_progress_bar(default_value=0, width=470)
            dpg.add_spacer(height=5)

            with dpg.group(horizontal=True):
                dpg.add_button(label="Start Conversion", callback=lambda:self.start_conversion_cb())
                dpg.add_button(label="Cancel", callback=lambda:self.cancel_processing_cb())
                self.thread_count_ID = dpg.add_input_int(label="Thread count", default_value=8, min_value=0, max_value=64, width=100, tag="threadCount")

        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)
        self.set_viewport_height(False, False)

        self.set_input_files(self.read_path_string("input"))

        pointcloud_header_open = False
        texture_header_open = False

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
            jobs = dpg.get_callback_queue()
            dpg.run_callbacks(jobs)

            if(dpg.is_item_left_clicked(header_pcSettings_ID)):
                pointcloud_header_open = not pointcloud_header_open
                self.set_viewport_height(pointcloud_header_open, texture_header_open)

            if(dpg.is_item_left_clicked(header_textureSettings_ID)):
                texture_header_open = not texture_header_open
                self.set_viewport_height(pointcloud_header_open, texture_header_open)

            if(self.conversionFinished):
                self.finish_conversion()
                self.conversionFinished = False

        # Shutdown threads when they are still running
        self.cancel_processing_cb()
        self.save_config()
        dpg.destroy_context()

if (__name__ == '__main__'):
    Tk().withdraw() # make sure Tkinter is loaded before starting DearPyGUI -- e.g. https://github.com/python/cpython/issues/90731
    UI = ConverterUI()
    UI.RunUI()