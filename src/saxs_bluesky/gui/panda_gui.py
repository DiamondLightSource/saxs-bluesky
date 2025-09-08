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
from dodal.common import inject

import saxs_bluesky.blueapi_configs
from saxs_bluesky._version import __version__
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


CONFIG = load_beamline_config(BL)
DEFAULT_PROFILE = CONFIG.DEFAULT_PROFILE
############################################################################################


class PandAGUI(tkinter.Tk):
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

        helpmenu = tkinter.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help Index", command=self.show_about)
        helpmenu.add_command(label="About...", command=self.show_about)
        menubar.add_cascade(label="Help", menu=helpmenu)

        self.window.config(menu=menubar)

        self.build_exp_run_frame()

        self.window.title("PandA Config")
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill="both", side="top", expand=True)

        for i in range(self.configuration.n_profiles):
            ProfileTab(self, self.notebook, self.configuration, i)
            # tab_names = self.notebook.tabs()
            # proftab_object: ProfileTab = self.notebook.nametowidget(tab_names[i])

        self.build_profile_edit_frame()

        ########################################################
        self.build_exp_info_frame()
        ######## #settings and buttons that apply to all profiles
        self.build_global_settings_frame()

        self.build_pulse_frame()
        self.build_active_detectors_frame()

        self.build_add_frame()

        #################################################################

        blueapi_config_path = f"{os.path.dirname(saxs_bluesky.blueapi_configs.__file__)}/{BL}_blueapi_config.yaml"  # noqa

        self.client = BlueAPIPythonClient(
            BL, blueapi_config_path, self.instrument_session
        )

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

            self.notebook.forget(self.add_frame)

            self.configuration.append_profile(DEFAULT_PROFILE)

            new_profile_tab = ProfileTab(
                self,
                self.notebook,
                self.configuration,
                len(self.configuration.profiles) - 1,
            )

            self.notebook.add(
                new_profile_tab, text=f"Profile {len(self.configuration.profiles) - 1}"
            )

            self.add_frame = tkinter.Frame()
            self.notebook.add(self.add_frame, text="+")
            self.window.bind("<<NotebookTabChanged>>", self.add_profile_tab)

            for n, _tab in enumerate(self.notebook.tabs()[0:-1]):
                self.notebook.tab(n, text="Profile " + str(n))

            self.notebook.select(self.notebook.tabs()[-2])

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

            self.notebook.select(self.notebook.tabs()[select_tab_index])
            self.configuration.delete_profile(index_to_del)
            self.notebook.forget(self.notebook.tabs()[index_to_del])
        elif answer and (self.configuration.n_profiles == 1):
            messagebox.showinfo("Info", "Must have atleast one profile")

        tab_names = self.notebook.tabs()

        for n, _tab in enumerate(self.notebook.tabs()[0:-1]):
            self.notebook.tab(n, text="Profile " + str(n))
            proftab_object: ProfileTab = self.notebook.nametowidget(tab_names[n])
            ttk.Label(proftab_object, text="Profile " + str(n)).grid(
                column=0, row=0, padx=5, pady=5, sticky="w"
            )

        return None

    def commit_config(self):
        tab_names = self.notebook.tabs()

        for i in range(self.configuration.n_profiles):
            proftab_object: ProfileTab = self.notebook.nametowidget(tab_names[i])
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

    def open_config(self):
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

        active_detectors = []

        for det in self.active_detectors_dict.keys():
            if self.active_detectors_dict[det].get() == 1:
                active_detectors.append(inject(det))

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

    def build_exp_run_frame(self):
        self.run_frame = ttk.Frame(self.window, borderwidth=5, relief="raised")

        self.run_frame.pack(fill="both", expand=True, side="right")
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

        open_config_button = ttk.Button(
            self.run_frame,
            text="Open Config",
            command=self.open_config,
        )
        open_config_button.grid(
            column=2, row=11, padx=5, pady=5, columnspan=1, sticky="news"
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

    def build_global_settings_frame(self):
        self.global_settings_frame = ttk.Frame(
            self.window, borderwidth=5, relief="raised"
        )

        self.global_settings_frame.pack(fill="both", expand=True, side="bottom")

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

        show_wiring_config_button = ttk.Button(
            self.global_settings_frame,
            text="Wiring config",
            command=self.show_wiring_config,
        )

        run_plan_button = ttk.Button(
            self.global_settings_frame, text="Run Plan", command=self.run_plan
        )

        load_button.pack(fill="both", expand=True, side="left")
        save_button.pack(fill="both", expand=True, side="left")
        configure_button.pack(fill="both", expand=True, side="left")
        show_wiring_config_button.pack(fill="both", expand=True, side="left")
        run_plan_button.pack(fill="both", expand=True, side="left")

    def return_profile_tab(self) -> ProfileTab:
        index = self.get_profile_index()
        tab_names = self.notebook.tabs()
        proftab_object: ProfileTab = self.notebook.nametowidget(tab_names[index])
        return proftab_object

    def build_profile_edit_frame(self):
        self.profile_edit_frame = ttk.Frame(self.window, borderwidth=5, relief="raised")
        self.profile_edit_frame.pack(fill="both", expand=True, side="top")

        self.proftab = self.return_profile_tab()

        self.insertrow_button = ttk.Button(
            self.profile_edit_frame,
            text="Insert Group",
            command=self.proftab.insert_group_button_action,
        )

        self.deleterow_button = ttk.Button(
            self.profile_edit_frame,
            text="Delete Group",
            command=self.proftab.delete_group_button_action,
        )

        self.appendrow_button = ttk.Button(
            self.profile_edit_frame,
            text="Add Group",
            command=self.proftab.append_group_button_action,
        )

        self.deletefinalrow_button = ttk.Button(
            self.profile_edit_frame,
            text="Discard Group",
            command=self.proftab.delete_last_groups_button_action,
        )

        self.delete_profile_button = ttk.Button(
            self.profile_edit_frame,
            text="Delete Profile",
            command=self.delete_profile_tab,
        )

        self.insertrow_button.pack(fill="both", expand=True, side="left")
        self.deleterow_button.pack(fill="both", expand=True, side="left")
        self.appendrow_button.pack(fill="both", expand=True, side="left")
        self.deletefinalrow_button.pack(fill="both", expand=True, side="left")
        self.delete_profile_button.pack(fill="both", expand=True, side="left")

    def build_add_frame(self):
        self.add_frame = tkinter.Frame()
        self.notebook.add(self.add_frame, text="+")
        self.window.bind("<<NotebookTabChanged>>", self.add_profile_tab)

    def build_exp_info_frame(self):
        self.experiment_settings_frame = ttk.Frame(
            self.window, borderwidth=5, relief="raised"
        )

        self.experiment_settings_frame.pack(
            fill="both", expand=True, side="bottom", anchor="w"
        )

        ttk.Label(
            self.experiment_settings_frame,
            text=f"Instrument: {BL}",
        ).grid(column=0, row=0, padx=5, pady=5, sticky="w")

        ttk.Label(
            self.experiment_settings_frame,
            text=f"Instrument Session: {self.instrument_session}",
        ).grid(column=0, row=1, padx=5, pady=5, sticky="w")

    def build_active_detectors_frame(self):
        self.active_detectors_dict = {}

        for pulse in range(CONFIG.PULSEBLOCKS):
            active_detectors_frame_n = ttk.Frame(
                self.pulse_frame, borderwidth=5, relief="raised"
            )

            active_detectors_frame_n.pack(
                fill="both", expand=True, side="left", anchor="w"
            )

            Pulselabel = ttk.Label(
                active_detectors_frame_n, text=f"Pulse Group: {pulse}"
            )

            Pulselabel.grid(column=0, row=0, padx=5, pady=5, sticky="w")

            # if pulse == 0:
            TTLLabel = ttk.Label(active_detectors_frame_n, text="TTL:")
            TTLLabel.grid(column=0, row=1, padx=5, pady=5, sticky="w")

            for n, det in enumerate(CONFIG.PULSE_CONNECTIONS[pulse + 1]):
                # experiment_var=tkinter.StringVar(value=self.configuration.experiment)

                var = tkinter.IntVar()

                if (det.lower() == "fs") or ("shutter" in det.lower()):
                    ad_entry = tkinter.Checkbutton(
                        active_detectors_frame_n,
                        bd=1,
                        text=det,
                        state="disabled",
                        variable=var,
                    )
                    ad_entry.select()
                else:
                    ad_entry = tkinter.Checkbutton(
                        active_detectors_frame_n,
                        bd=1,
                        text=det,
                        variable=var,
                    )

                if det in self.configuration.detectors:
                    ad_entry.select()

                ad_entry.grid(column=n + 1, row=1, padx=5, pady=5, sticky="w")

                if det.lower() != "fs":
                    self.active_detectors_dict[det] = var

    def build_pulse_frame(self):
        self.pulse_frame = ttk.Frame(self.window, borderwidth=5, relief="raised")
        self.pulse_frame.pack(fill="both", side="left", expand=True)
        Outlabel = ttk.Label(self.pulse_frame, text="Enable Device")
        Outlabel.pack(fill="both", side="top", expand=True)


if __name__ == "__main__":
    # Use the following url
    # https://github.com/DiamondLightSource/blueapi/blob/main/src/blueapi/client/client.py
    # blueapi -c i22_blueapi_config.yaml controller run count '{"detectors":["saxs"]}'

    # dir_path = os.path.dirname(os.path.realpath(__file__))
    # config_filepath = os.path.join(dir_path, "profile_yamls", "panda_config.yaml")
    PandAGUI(configuration=CONFIG.DEFAULT_EXPERIMENT)
