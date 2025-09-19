#!/dls/science/users/akz63626/i22/i22_venv/bin/python


"""

Python dataclasses and GUI as a replacement for NCDDetectors

"""

import copy
import json
import os
import tkinter
from tkinter import filedialog, messagebox, ttk
from tkinter.simpledialog import askstring

import matplotlib.pyplot as plt
from bluesky.plans import count
from ttkthemes import ThemedTk

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
        ask_instrument_session: bool = False,
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

        if ask_instrument_session and self.configuration.instrument_session is not None:
            self.instrument_session = self.request_instrument_session()
        elif self.configuration.instrument_session is None:
            self.instrument_session = self.request_instrument_session()
        else:
            self.instrument_session = self.configuration.instrument_session

        blueapi_config_path = f"{os.path.dirname(saxs_bluesky.blueapi_configs.__file__)}/{BL}_blueapi_config.yaml"  # noqa

        self.client = BlueAPIPythonClient(
            BL, blueapi_config_path, self.instrument_session
        )

        self.window = ThemedTk(theme="arc")
        self.window.wm_resizable(True, True)
        self.window.minsize(600, 200)
        self.window.title("PandA Config")
        self.style = ttk.Style(self.window)

        # self.theme("dark")

        self.build_menu_bar()

        self.always_visible_frame = ttk.Frame(self.window, borderwidth=5)
        self.always_visible_frame.pack(fill="both", side="bottom", expand=True)
        self.build_blueapi_frame()

        self.notebook = ttk.Notebook(self.always_visible_frame)
        self.notebook.pack(fill="none", side="top", expand=False)

        #################3

        #################

        for n, profile in enumerate(self.configuration.profiles):
            profile_tab = ProfileTab(self.notebook, profile)
            profile_tab.pack(fill="y", expand=False, side="left")

            self.notebook.add(profile_tab, text="Profile " + str(n))

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

    def build_menu_bar(self):
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

        instr_menu = tkinter.Menu(menubar, tearoff=0)
        instr_menu.add_command(
            label="Change Instrument Session", command=self.change_intrument_session
        )
        menubar.add_cascade(label="Inst Session", menu=instr_menu)

        theme_menu = tkinter.Menu(menubar, tearoff=0)
        all_themes = self.window.pixmap_themes + ["clam", "default", "alt", "classic"]

        theme_menu.add_command(
            label=all_themes[0],
            command=lambda *ignore: self.window.set_theme(all_themes[0]),
        )
        theme_menu.add_command(
            label=all_themes[1],
            command=lambda *ignore: self.window.set_theme(all_themes[1]),
        )
        theme_menu.add_command(
            label=all_themes[2],
            command=lambda *ignore: self.window.set_theme(all_themes[2]),
        )
        theme_menu.add_command(
            label=all_themes[3],
            command=lambda *ignore: self.window.set_theme(all_themes[3]),
        )
        theme_menu.add_command(
            label=all_themes[4],
            command=lambda *ignore: self.window.set_theme(all_themes[4]),
        )
        theme_menu.add_command(
            label=all_themes[5],
            command=lambda *ignore: self.window.set_theme(all_themes[5]),
        )
        theme_menu.add_command(
            label=all_themes[6],
            command=lambda *ignore: self.window.set_theme(all_themes[6]),
        )
        theme_menu.add_command(
            label=all_themes[7],
            command=lambda *ignore: self.window.set_theme(all_themes[7]),
        )
        theme_menu.add_command(
            label=all_themes[8],
            command=lambda *ignore: self.window.set_theme(all_themes[8]),
        )
        theme_menu.add_command(
            label=all_themes[9],
            command=lambda *ignore: self.window.set_theme(all_themes[9]),
        )
        theme_menu.add_command(
            label=all_themes[10],
            command=lambda *ignore: self.window.set_theme(all_themes[10]),
        )

        theme_menu.add_command(
            label=all_themes[11],
            command=lambda *ignore: self.window.set_theme(all_themes[11]),
        )
        theme_menu.add_command(
            label=all_themes[12],
            command=lambda *ignore: self.window.set_theme(all_themes[12]),
        )
        # theme_menu.add_command(
        #     label=all_themes[1] + "dark",
        #     command=lambda *ignore: self.window.set_theme_advanced(
        #         all_themes[1] + "dark", brightness=0
        #     ),
        # )

        menubar.add_cascade(label="Theme", menu=theme_menu)

        helpmenu = tkinter.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help Index", command=self.show_about)
        helpmenu.add_command(label="About...", command=self.show_about)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.window.config(menu=menubar)

    def request_instrument_session(self):
        self.instrument_session = str(
            askstring(
                "Instrument Session",
                "Enter an intrument session:",
                initialvalue=self.configuration.instrument_session,
            )
        )

        if self.instrument_session is None:
            messagebox.showinfo(
                "Instrument Session", "Instrument Session must not be None!"
            )
            self.request_instrument_session()

        return self.instrument_session

    def change_intrument_session(self):
        self.instrument_session = self.request_instrument_session()

        text_list = [
            f"Instrument: {BL}",
            f"Instrument Session: {self.instrument_session}",
        ]

        for label, text in zip(self.info_labels, text_list, strict=False):
            label.set(text)

        self.client.change_session(self.instrument_session)

    def open_new_window(self):
        PandAGUI()

    def show_about(self):
        messagebox.showinfo("About", __version__)

    # def theme(self, theme_name: str = "arc"):
    #     self.window.set_theme(theme_name)

    def add_profile_tab(self, event):
        if self.notebook.select() == self.notebook.tabs()[-1]:
            print("new profile tab created")

            self.commit_config()

            self.notebook.forget(self.add_frame)

            self.configuration.append_profile(copy.deepcopy(DEFAULT_PROFILE))
            index = len(self.configuration.profiles) - 1

            new_profile_tab = ProfileTab(
                self.notebook,
                self.configuration.profiles[index],
            )

            self.notebook.add(new_profile_tab, text=f"Profile {index}")

            self.build_add_tab()  # re add tab +

            for n in range(self.configuration.n_profiles):
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

            all_profile_tabs = self.return_all_profile_tabs()

            self.notebook.select(
                all_profile_tabs[select_tab_index]
            )  # select the one before
            self.configuration.delete_profile(index_to_del)
            self.notebook.forget(all_profile_tabs[index_to_del])

        elif answer and (self.configuration.n_profiles == 1):
            messagebox.showinfo("Info", "Must have atleast one profile")

        ##rename all the tabs
        for n, _tab in enumerate(self.notebook.tabs()[0:-1]):
            self.notebook.tab(n, text="Profile " + str(n))

        return None

    def commit_config(self):
        # tab_names = self.notebook.tabs()

        self.configuration.instrument_session = self.instrument_session
        self.configuration.detectors = (
            self.active_detectors_frame.get_active_detectors()
        )

        profile_tabs = self.return_all_profile_tabs()

        for n, profile_tab in enumerate(profile_tabs):
            profile_tab.edit_config_for_profile()
            self.configuration.profiles[n] = profile_tab.profile

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

    def configure_panda(self):
        self.commit_config()

        index = self.get_profile_index()

        profile_to_upload = self.configuration.profiles[index]
        active_detectors = self.active_detectors_frame.get_active_detectors()

        print(profile_to_upload)
        print(active_detectors)

        # params = {"profile": profile_to_upload, "detectors": active_detectors}

        try:
            self.client.run(
                configure_panda_triggering,
                profile=profile_to_upload,
                detectors=active_detectors,
            )
        except ConnectionError:
            print("Could not upload profile to panda")

    def run_plan(self):
        try:
            self.client.run(run_panda_triggering)
        except ConnectionError:
            print("Could not upload profile to panda")

    def set_detectors_plan(self):
        # params = {
        #     "detectors": list(self.active_detectors_frame.get_active_detectors()),
        # }

        try:
            self.client.run(
                set_detectors,
                detectors=list(self.active_detectors_frame.get_active_detectors()),
            )
        except ConnectionError:
            print("Could not upload profile to panda")

    def log_detectors_plan(self):
        try:
            self.client.run(log_detectors)
        except ConnectionError:
            print("Could not upload profile to panda")

    def count_detectors(self):
        # params = {
        #     "detectors": list(self.active_detectors_frame.get_active_detectors()),
        # }

        try:
            self.client.run(
                count,
                detectors=list(self.active_detectors_frame.get_active_detectors()),
            )
        except ConnectionError:
            print("Could not upload profile to panda")

    def open_step_widget(self):
        StepWidget(
            list(self.active_detectors_frame.get_active_detectors()), self.client
        )

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
            self.run_frame, text="Stop Plan", command=self.client.stop
        )
        stop_plans_button.grid(
            column=2, row=5, padx=5, pady=5, columnspan=1, sticky="news"
        )

        pause_plans_button = ttk.Button(
            self.run_frame, text="Pause Plan", command=self.client.pause
        )
        pause_plans_button.grid(
            column=2, row=7, padx=5, pady=5, columnspan=1, sticky="news"
        )

        resume_plans_button = ttk.Button(
            self.run_frame, text="Resume Plan", command=self.client.resume
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
            self.run_frame, text="Reload Env", command=self.client.reload_environment
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

        def print_prof():
            self.get_profile_tab().print_profile_button_action()

        profile_print = ttk.Button(
            self.run_frame,
            text="Print Profile",
            command=print_prof,
        )
        profile_print.grid(
            column=2, row=18, padx=5, pady=5, columnspan=1, sticky="news"
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

    def return_all_profile_tabs(self) -> list[ProfileTab]:
        tab_names = self.notebook.tabs()[:-1]  # miss last one because it the + tab

        print(tab_names)

        all_profile_tabs = [
            self.notebook.nametowidget(tab_names[p]) for p in range(len(tab_names))
        ]
        return all_profile_tabs

    def get_profile_tab(self) -> ProfileTab:
        index = self.get_profile_index()
        tab_names = self.notebook.tabs()
        profile_tab: ProfileTab = self.notebook.nametowidget(tab_names[index])
        return profile_tab

    def set_profile_tab(self):
        self.profile_tab = self.get_profile_tab()

    def build_add_tab(self):
        for n, profile in enumerate(self.configuration.profiles):
            print(f"profile {n} id:", id(profile))

        self.add_frame = ttk.Frame()
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

        self.info_labels = []

        for n, text in enumerate(text_list):
            labelVar = tkinter.StringVar(value=text)

            info_label = ttk.Label(
                self.experiment_settings_frame,
                textvariable=labelVar,
            )

            info_label.grid(column=n * 2, row=0, padx=5, pady=5, sticky="news")

            ttk.Label(
                self.experiment_settings_frame,
                text=seperator,
            ).grid(column=(n * 2) + 1, row=0, padx=5, pady=5, sticky="news")

            self.info_labels.append(labelVar)

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
