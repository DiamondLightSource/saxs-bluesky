#!/dls/science/users/akz63626/i22/i22_venv/bin/python


"""

Python dataclasses and GUI as a replacement for NCDDetectors

"""

import json
import os
import tkinter
from tkinter import filedialog, messagebox, ttk
from tkinter.simpledialog import askstring

import matplotlib.pyplot as plt

import saxs_bluesky.blueapi_configs
from saxs_bluesky._version import __version__
from saxs_bluesky.gui.gui_frames import ActiveDetectorsFrame
from saxs_bluesky.gui.panda_gui_elements import ProfileTab
from saxs_bluesky.gui.step_gui import StepWidget
from saxs_bluesky.plans.ncd_panda import (
    configure_panda_triggering,
    log_detectors,
    run_panda_triggering,
    set_detectors,
)
from saxs_bluesky.utils.beamline_client import BlueAPIPythonClient
from saxs_bluesky.utils.profile_groups import ExperimentLoader
from saxs_bluesky.utils.utils import (
    get_saxs_beamline,
    load_beamline_config,
)

############################################################################################

BL = get_saxs_beamline()


CONFIG = load_beamline_config()
DEFAULT_PROFILE = CONFIG.DEFAULT_PROFILE
############################################################################################


class PandAGUI:
    def __init__(
        self,
        panda_config_yaml: str | None = None,
        configuration: ExperimentLoader | None = None,
        start: bool = True,
    ):
        self.panda_config_yaml = panda_config_yaml
        self.default_config_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "profile_yamls",
            "default_panda_config.yaml",
        )

        if (self.panda_config_yaml is None) and (configuration is None):
            self.configuration = ExperimentLoader.read_from_yaml(
                self.default_config_path
            )
        elif (self.panda_config_yaml is not None) and (configuration is None):
            self.configuration = ExperimentLoader.read_from_yaml(self.panda_config_yaml)
        elif (self.panda_config_yaml is None) and (configuration is not None):
            self.configuration = configuration
        else:
            print(
                "Must pass either panda_config_yaml or configuration object. Not both"
            )
            quit()

        self.instrument_session = str(
            askstring(
                "Instrument Session",
                "Enter an intrument session:",
                initialvalue=self.configuration.instrument_session,
            )
        )

        blueapi_config_path = f"{os.path.dirname(saxs_bluesky.blueapi_configs.__file__)}/{BL}_blueapi_config.yaml"  # noqa

        self.client = BlueAPIPythonClient(
            BL, blueapi_config_path, self.instrument_session
        )

        self.profiles = self.configuration.profiles

        self.window = tkinter.Tk()
        self.window.wm_resizable(True, True)
        self.window.minsize(600, 200)
        self.theme(CONFIG.THEME_NAME)

        menubar = tkinter.Menu(self.window)
        filemenu = tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.open_new_window)
        filemenu.add_command(label="Open", command=self.load_config)
        filemenu.add_command(label="Save", command=self.save_config)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.window.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        config_menu = tkinter.Menu(menubar, tearoff=0)
        config_menu.add_command(label="Edit Config", command=self.open_settings)
        menubar.add_cascade(label="Config", menu=config_menu)

        show_menu = tkinter.Menu(menubar, tearoff=0)
        show_menu.add_command(label="Show Wiring", command=self.show_wiring_config)
        menubar.add_cascade(label="Show", menu=show_menu)

        helpmenu = tkinter.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help Index", command=self.show_about)
        helpmenu.add_command(label="About...", command=self.show_about)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.window.config(menu=menubar)

        self.window.title("PandA Config")

        self.always_visible_frame = ttk.Frame(self.window, borderwidth=5)
        self.always_visible_frame.pack(fill="both", side="bottom", expand=True)
        self.build_blueapi_frame()

        self.notebook = ttk.Notebook(self.always_visible_frame)
        self.notebook.pack(fill="none", side="top", expand=False)

        #################3

        #################

        self.profile_tabs: list[ProfileTab] = []

        for n, profile in enumerate(self.configuration.profiles):
            profile_tab = ProfileTab(self.notebook, profile)
            profile_tab.pack(fill="y", expand=False, side="left")

            self.notebook.add(profile_tab, text="Profile " + str(n))
            self.profile_tabs.append(profile_tab)

        def print_prof():
            self.get_profile_tab().print_profile_button_action()

        print_profile_button = ttk.Button(
            self.run_frame,
            text="Print Profile",
            command=print_prof,
        )
        print_profile_button.grid(
            column=2, row=11, padx=5, pady=5, columnspan=1, sticky="news"
        )

        # x = ttk.Button(
        #     self.run_frame,
        #     text="Print Profile",
        #     command=self.get_profile_tab.print_profile_button_action,
        # )
        # x.grid(column=2, row=20, padx=5, pady=5, columnspan=1, sticky="news")

        # print(self.get_profile_index())

        ########################################################

        text_list = [
            f"Instrument: {BL}",
            f"Instrument Session: {self.instrument_session}",
        ]

        self.build_exp_info_frame(text_list)
        # ######## #settings and buttons that apply to all profiles

        self.build_add_tab()

        self.build_global_settings_frame(side="left")

        self.active_detectors_frame = ActiveDetectorsFrame(
            self.always_visible_frame,
            CONFIG.PULSEBLOCKS,
            CONFIG.PULSE_CONNECTIONS,
            self.configuration.detectors,
        )
        self.build_profile_edit_frame(side="left")

        #################################################################

        if start:
            self.window.mainloop()

    def open_new_window(self):
        PandAGUI()

    def show_about(self):
        messagebox.showinfo("About", __version__)

    def theme(self, theme_name: str):
        style = ttk.Style(self.window)
        print("All themes:", style.theme_names())
        style.theme_use(theme_name)

    def add_profile_tab(self, event):
        if self.notebook.select() == self.notebook.tabs()[-1]:
            print("new profile tab created")

            self.commit_config()

            self.notebook.forget(self.add_frame)

            print(self.configuration.profiles)

            self.configuration.append_profile(DEFAULT_PROFILE)
            index = len(self.configuration.profiles) - 1

            print(self.configuration.profiles)

            new_profile_tab = ProfileTab(
                self.notebook,
                self.configuration.profiles[index],
            )

            self.notebook.add(new_profile_tab, text=f"Profile {index}")
            self.profile_tabs.append(new_profile_tab)

            self.add_frame = tkinter.Frame()
            self.notebook.add(self.add_frame, text="+")
            self.window.bind("<<NotebookTabChanged>>", self.add_profile_tab)

            for n, _tab in enumerate(self.notebook.tabs()[0:-1]):
                self.notebook.tab(n, text="Profile " + str(n))

            self.notebook.select(
                self.notebook.tabs()[-2]
            )  # select the second to last one, ie not the + tab
            # (which would cause an infinite loop)

    def delete_profile_tab(self):
        answer = messagebox.askyesno(
            "Close Profile", "Delete this profile? Are you sure?"
        )

        if answer and (self.configuration.n_profiles >= 2):
            index_to_del = self.get_profile_index()

            if index_to_del == 0:
                select_tab_index = 1
            else:
                select_tab_index = index_to_del - 1

            self.notebook.select(
                self.profile_tabs[select_tab_index]
            )  # select the one before
            self.configuration.delete_profile(index_to_del)
            self.notebook.forget(self.profile_tabs[index_to_del])
            self.profile_tabs.pop(index_to_del)

        elif answer and (self.configuration.n_profiles == 1):
            messagebox.showinfo("Info", "Must have atleast one profile")

        ##rename all the tabs
        for n, _tab in enumerate(self.notebook.tabs()[0:-1]):
            self.notebook.tab(n, text="Profile " + str(n))
            # proftab_object: ProfileTab = self.profile_tabs[n]
            # ttk.Label(proftab_object, text="Profile " + str(n)).grid(
            #     column=0, row=0, padx=5, pady=5, sticky="w"
            # )

        return None

    def commit_config(self):
        # tab_names = self.notebook.tabs()

        for i in range(self.configuration.n_profiles):
            proftab_object: ProfileTab = self.profile_tabs[i]
            proftab_object.edit_config_for_profile()

    def load_config(self):
        panda_config_yaml = filedialog.askopenfilename()

        if (len(panda_config_yaml)) != 0:
            answer = messagebox.askyesno(
                "Close/Open New", "Finished editing this profile? Continue?"
            )

            if answer:
                self.window.destroy()
                PandAGUI(panda_config_yaml)
            else:
                return

    def save_config(self):
        panda_config_yaml = filedialog.asksaveasfile(
            mode="w", defaultextension=".yaml", filetypes=[("yaml", ".yaml")]
        )

        if panda_config_yaml:
            self.commit_config()
            self.configuration.save_to_yaml(panda_config_yaml.name)

            config_dict = self.configuration.to_dict()

            with open(panda_config_yaml.name.replace("yaml", "json"), "w") as fpo:
                json.dump(config_dict, fpo, indent=2)

    def open_settings(self):
        try:
            os.system(f"gedit {CONFIG.__file__} &")
        except FileNotFoundError as e:
            print(e)

    def show_wiring_config(self):
        fig, ax = plt.subplots(1, 1, figsize=(16, 8))

        labels = ["TTLIN", "LVDSIN", "TTLOUT", "LVDSOUT"]

        for key in CONFIG.TTLIN.keys():
            INDev = CONFIG.TTLIN[key]

            ax.scatter(0, key, color="k", s=50)
            ax.text(0 + 0.1, key, INDev)

        for key in CONFIG.LVDSIN.keys():
            LVDSINDev = CONFIG.LVDSIN[key]

            ax.scatter(1, key, color="k", s=50)
            ax.text(1 + 0.1, key, LVDSINDev)

        for key in CONFIG.TTLOUT.keys():
            TTLOUTDev = CONFIG.TTLOUT[key]

            ax.scatter(2, key, color="b", s=50)
            ax.text(2 + 0.1, key, TTLOUTDev)

        for key in CONFIG.LVDSOUT.keys():
            LVDSOUTDev = CONFIG.LVDSOUT[key]
            ax.scatter(3, key, color="b", s=50)
            ax.text(3 + 0.1, key, LVDSOUTDev)

        ax.set_ylabel("I/O Connections")
        ax.grid()
        ax.set_xlim(-0.2, 4)
        plt.gca().invert_yaxis()
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=90)
        plt.show()

    def get_plans(self):
        plans = self.client.get_plans().plans

        for plan in plans:
            print(plan.name, "\n")

    def get_devices(self):
        devices = self.client.get_devices().devices

        for dev in devices:
            print(dev, "\n\n")

    def get_profile_index(self):
        index = int(self.notebook.index("current"))
        return index

    def get_profile_tab(self) -> ProfileTab:
        profile_tab = self.profile_tabs[self.get_profile_index()]
        return profile_tab

    def configure_panda(self):
        self.commit_config()

        index = self.get_profile_index()

        profile_to_upload = self.configuration.profiles[index]
        active_detectors = self.active_detectors_frame.get_active_detectors()

        print(profile_to_upload)
        print(active_detectors)

        params = {"profile": profile_to_upload, "detectors": active_detectors}

        try:
            self.client.run(configure_panda_triggering.__name__, params)
        except ConnectionError:
            print("Could not upload profile to panda")

    def run_plan(self):
        try:
            self.client.run(run_panda_triggering.__name__, {})
        except ConnectionError:
            print("Could not upload profile to panda")

    def set_detectors_plan(self):
        params = {
            "detectors": list(CONFIG.FAST_DETECTORS),
        }

        try:
            self.client.run(set_detectors.__name__, params)
        except ConnectionError:
            print("Could not upload profile to panda")

    def log_detectors_plan(self):
        try:
            self.client.run(log_detectors.__name__, {})
        except ConnectionError:
            print("Could not upload profile to panda")

    def count_detectors(self):
        params = {
            "detectors": list(CONFIG.FAST_DETECTORS),
        }

        try:
            self.client.run("count", params)
        except ConnectionError:
            print("Could not upload profile to panda")

    def stop_plan(self):
        self.client.stop()

    def reload_environment(self):
        self.client.reload_environment()

    def pause_plan(self):
        self.client.pause()

    def resume_plan(self):
        self.client.resume()

    def open_step_widget(self):
        StepWidget(self.instrument_session)

    def show_active_detectors(self):
        active_detectors = self.active_detectors_frame.get_active_detectors()
        print(active_detectors)

    def build_blueapi_frame(self):
        self.run_frame = ttk.Frame(self.always_visible_frame, borderwidth=5)

        self.run_frame.pack(fill="y", expand=True, side="right")
        get_plans_button = ttk.Button(
            self.run_frame, text="Get Plans", command=self.get_plans
        )
        get_plans_button.grid(
            column=2, row=1, padx=5, pady=5, columnspan=1, sticky="news"
        )

        get_devices_button = ttk.Button(
            self.run_frame, text="Get Devices", command=self.get_devices
        )
        get_devices_button.grid(
            column=2, row=3, padx=5, pady=5, columnspan=1, sticky="news"
        )

        stop_plans_button = ttk.Button(
            self.run_frame, text="Stop Plan", command=self.stop_plan
        )
        stop_plans_button.grid(
            column=2, row=5, padx=5, pady=5, columnspan=1, sticky="news"
        )

        pause_plans_button = ttk.Button(
            self.run_frame, text="Pause Plan", command=self.pause_plan
        )
        pause_plans_button.grid(
            column=2, row=7, padx=5, pady=5, columnspan=1, sticky="news"
        )

        resume_plans_button = ttk.Button(
            self.run_frame, text="Resume Plan", command=self.resume_plan
        )
        resume_plans_button.grid(
            column=2,
            row=9,
            padx=5,
            pady=5,
            columnspan=1,
            sticky="news",
        )

        reload_env_button = ttk.Button(
            self.run_frame, text="Reload Env", command=self.reload_environment
        )
        reload_env_button.grid(
            column=2, row=12, padx=5, pady=5, columnspan=1, sticky="news"
        )

        set_det_button = ttk.Button(
            self.run_frame, text="Set dets", command=self.set_detectors_plan
        )
        set_det_button.grid(
            column=2, row=13, padx=5, pady=5, columnspan=1, sticky="news"
        )

        show_det_button = ttk.Button(
            self.run_frame, text="Log dets", command=self.log_detectors_plan
        )
        show_det_button.grid(
            column=2, row=14, padx=5, pady=5, columnspan=1, sticky="news"
        )

        step_widget_button = ttk.Button(
            self.run_frame, text="Open Step Widget", command=self.open_step_widget
        )
        step_widget_button.grid(
            column=2, row=15, padx=5, pady=5, columnspan=1, sticky="news"
        )

        count_det_button = ttk.Button(
            self.run_frame, text="Count Detector", command=self.count_detectors
        )
        count_det_button.grid(
            column=2, row=16, padx=5, pady=5, columnspan=1, sticky="news"
        )

        active_det_button = ttk.Button(
            self.run_frame,
            text="Show Active Detectors",
            command=self.show_active_detectors,
        )
        active_det_button.grid(
            column=2, row=17, padx=5, pady=5, columnspan=1, sticky="news"
        )

        return None

    def build_global_settings_frame(self, side: str = "left"):
        self.global_settings_frame = ttk.Frame(self.always_visible_frame, borderwidth=5)

        self.global_settings_frame.pack(fill="x", expand=True, side="bottom")

        # add a load/save/configure button
        load_button = ttk.Button(
            self.global_settings_frame, text="Load", command=self.load_config
        )

        save_button = ttk.Button(
            self.global_settings_frame, text="Save", command=self.save_config
        )

        configure_button = ttk.Button(
            self.global_settings_frame,
            text="Upload to PandA",
            command=self.configure_panda,
        )

        run_plan_button = ttk.Button(
            self.global_settings_frame, text="Trigger PandA", command=self.run_plan
        )

        load_button.pack(fill="both", expand=True, side=side)  # type: ignore
        save_button.pack(fill="both", expand=True, side=side)  # type: ignore
        configure_button.pack(fill="both", expand=True, side=side)  # type: ignore
        run_plan_button.pack(fill="both", expand=True, side=side)  # type: ignore

        return None

    def return_profile_tab(self) -> ProfileTab:
        index = self.get_profile_index()
        tab_names = self.notebook.tabs()
        proftab_object: ProfileTab = self.notebook.nametowidget(tab_names[index])
        return proftab_object

    def set_profile_tab(self):
        self.proftab = self.return_profile_tab()

    def build_add_tab(self):
        self.add_frame = tkinter.Frame()
        self.notebook.add(self.add_frame, text="+")
        self.window.bind("<<NotebookTabChanged>>", self.add_profile_tab)

        return None

    def build_exp_info_frame(self, text_list, seperator=" | "):
        self.experiment_settings_frame = ttk.Frame(
            self.always_visible_frame, borderwidth=5
        )

        self.experiment_settings_frame.pack(
            fill="both", expand=True, side="bottom", anchor="n"
        )

        for n, text in enumerate(text_list):
            ttk.Label(
                self.experiment_settings_frame,
                text=text,
            ).grid(column=n * 2, row=0, padx=5, pady=5, sticky="news")

            ttk.Label(
                self.experiment_settings_frame,
                text=seperator,
            ).grid(column=(n * 2) + 1, row=0, padx=5, pady=5, sticky="news")

        return None

    def build_profile_edit_frame(self, side: str = "left"):
        self.profile_edit_frame = ttk.Frame(self.always_visible_frame, borderwidth=5)
        self.profile_edit_frame.pack(fill="both", expand=True, side="left")

        def insert():
            self.get_profile_tab().insert_group_button_action()

        insertrow_button = ttk.Button(
            self.profile_edit_frame,
            text="Insert Group",
            command=insert,
        )

        def delete():
            self.get_profile_tab().delete_group_button_action()

        deleterow_button = ttk.Button(
            self.profile_edit_frame,
            text="Delete Group",
            command=delete,
        )

        def append():
            self.get_profile_tab().append_group_button_action()

        appendrow_button = ttk.Button(
            self.profile_edit_frame,
            text="Add Group",
            command=append,
        )

        def discard():
            self.get_profile_tab().delete_last_groups_button_action()

        discardrow_button = ttk.Button(
            self.profile_edit_frame,
            text="Discard Group",
            command=discard,
        )

        delete_profile_button = ttk.Button(
            self.profile_edit_frame,
            text="Delete Profile",
            command=self.delete_profile_tab,
        )

        insertrow_button.pack(fill="x", expand=True, side=side)  # type: ignore
        deleterow_button.pack(fill="x", expand=True, side=side)  # type: ignore
        appendrow_button.pack(fill="x", expand=True, side=side)  # type: ignore
        discardrow_button.pack(fill="x", expand=True, side=side)  # type: ignore
        delete_profile_button.pack(fill="x", expand=True, side=side)  # type: ignore

        return None


if __name__ == "__main__":
    # Use the following url
    # https://github.com/DiamondLightSource/blueapi/blob/main/src/blueapi/client/client.py
    # blueapi -c i22_blueapi_config.yaml controller run count '{"detectors":["saxs"]}'

    # dir_path = os.path.dirname(os.path.realpath(__file__))
    # config_filepath = os.path.join(dir_path, "profile_yamls", "panda_config.yaml")
    PandAGUI(configuration=CONFIG.DEFAULT_EXPERIMENT)
