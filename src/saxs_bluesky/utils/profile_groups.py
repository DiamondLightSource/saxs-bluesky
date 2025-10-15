from copy import deepcopy
from pathlib import Path
from string import ascii_lowercase
from typing import Any

import numpy as np
import yaml
from ophyd_async.core import DetectorTrigger, TriggerInfo, in_micros
from ophyd_async.fastcs.panda import SeqTable, SeqTableInfo, SeqTrigger
from pydantic import BaseModel

from saxs_bluesky.utils.ncdcore import NCDCore

"""

Group and Profile BaseModels

"""


class Group(BaseModel):
    """A Group represents the information of one line in the PandA sequence table.
    Additional information is stored and used for configuration in the GUI
    This can be used alonside the Profile class
    to build up complex experimental profiles"""

    frames: int
    trigger: str
    wait_time: int
    wait_units: str
    run_time: int
    run_units: str
    wait_pulses: list[int]
    run_pulses: list[int]

    def model_post_init(self, __context: Any) -> None:
        assert len(self.wait_pulses) == len(self.run_pulses)
        self.run_units = self.run_units.upper()
        self.wait_units = self.wait_units.upper()
        self.trigger = self.trigger.upper()

    @property
    def wait_time_s(self) -> float:
        return self.wait_time * NCDCore.to_seconds(self.wait_units)

    @property
    def run_time_s(self) -> float:
        return self.run_time * NCDCore.to_seconds(self.run_units)

    @property
    def group_duration(self) -> float:
        return (self.wait_time_s + self.run_time_s) * self.frames

    @property
    def active(self) -> bool:
        if (sum(self.wait_pulses) + sum(self.run_pulses)) > 0:
            return True
        else:
            return False

    def seq_row(self) -> SeqTable:
        if not self.trigger:
            trigger = SeqTrigger.IMMEDIATE
        elif self.trigger == "FALSE":
            trigger = SeqTrigger.IMMEDIATE
            self.trigger = "IMMEDIATE"
        else:
            trigger = eval(f"{SeqTrigger.__name__}.{self.trigger}")

        seq_table_kwargs = {
            "repeats": self.frames,
            "trigger": trigger,
            "position": 0,
            "time1": in_micros(self.wait_time_s),
        }

        alphabet = list(ascii_lowercase)

        out1 = {
            f"out{alphabet[f]}1": self.wait_pulses[f]
            for f in range(len(self.wait_pulses))
        }
        seq_table_kwargs.update(out1)

        seq_table_kwargs.update({"time2": in_micros(self.run_time_s)})

        out2 = {
            f"out{alphabet[f]}2": self.run_pulses[f]
            for f in range(len(self.run_pulses))
        }
        seq_table_kwargs.update(out2)

        seq_table = SeqTable.row(**seq_table_kwargs)

        return seq_table


class Profile(BaseModel):
    """A basemodel for all the information needed to configure the PandA triggering.
    Repeats are the number of times the who sequence table is run
    Seq trigger must be set to either immediate or one of the panda trigger types.
    A group is effectively a line in the sequencer table
    Multiplier is use when the PandA is set up for triggering different
    sets of detetcors at different rates
    The information stored in this BaseModel can be passed to ncd_panda and applied.
    The information can also be used to configure it in the gui"""

    repeats: int = 1
    seq_trigger: str = "Immediate"
    groups: list[Group] = []
    multiplier: list[int] | None = None

    @property
    def total_frames(self) -> int:
        total_frames = 0
        for n_group in self.groups:
            total_frames += n_group.frames
        return total_frames

    @property
    def n_groups(self):
        return len(self.groups)

    @property
    def duration_per_repeat(self) -> float:
        duration_per_repeat = 0

        for n_group in self.groups:
            duration_per_repeat += n_group.group_duration
        return duration_per_repeat

    @property
    def max_livetime(self) -> float:
        return np.amax([g.run_time_s for g in self.groups])

    @property
    def duration(self) -> float:
        duration = self.duration_per_repeat * self.repeats
        return duration

    @property
    def seq_table_info(self) -> SeqTableInfo:
        seq_table_info = SeqTableInfo(
            sequence_table=self.seq_table, repeats=self.repeats
        )

        return seq_table_info

    @property
    def active_pulses(self) -> list[int]:
        """
        Checks which outputs are active in the wait phase,
        checks which outputs are active in the run phase
        and returns a list of active outputs. Because python uses 0-based indexing
        while the Panda uses 1-based indexing,
        the output indices are adjusted accordingly.
        """
        wait_matrix = np.array([g.wait_pulses for g in self.groups])
        run_matrix = np.array([g.run_pulses for g in self.groups])
        active_matrix = wait_matrix + run_matrix
        active_pulses = np.where((np.sum(active_matrix, axis=0)) != 0)[0] + 1
        active_pulses = active_pulses.tolist()

        return active_pulses

    @property
    def triggers(self) -> list[int]:
        # [3, 1, 1, 1, 1] or something
        return [group.frames for group in self.groups if group.active]

    def return_trigger_info(
        self,
        max_deadtime: float,
        trigger_type=DetectorTrigger.VARIABLE_GATE,
    ) -> TriggerInfo:
        trigger_info = TriggerInfo(
            number_of_events=self.number_of_events,
            trigger=trigger_type,  # or maybe EDGE_TRIGGER or #VARIABLE_GATE
            deadtime=max_deadtime + ((max_deadtime) / 10),
            livetime=self.max_livetime,
            exposures_per_event=1,
            exposure_timeout=self.duration + 1,
        )

        return trigger_info

    @property
    def number_of_events(self) -> list[int]:
        return self.triggers * self.repeats

    def append_group(self, group: Group) -> None:
        self.groups.append(deepcopy(group))

    def delete_group(self, n: int) -> None:
        self.groups.pop(n)

    def insert_group(self, n: int, group: Group):
        self.groups.insert(n, deepcopy(group))

    @property
    def seq_table(self) -> SeqTable:
        seq_tables = (group.seq_row() for group in self.groups)

        seq = seq_tables.__next__()
        for table in seq_tables:
            seq = seq + table

        return seq

    @staticmethod
    def inputs() -> list[str]:
        ttl_ins = [f"TTLIN{f + 1}" for f in range(6)]
        lvds_ins = [f"LVDSIN{f + 1}" for f in range(2)]
        return ttl_ins + lvds_ins

    @staticmethod
    def seq_triggers() -> list[str]:
        return list(SeqTrigger.__dict__["_member_names_"])

    @staticmethod
    def outputs() -> list[str]:
        ttl_outs = [f"TTLOUT{f + 1}" for f in range(10)]
        lvds_outs = [f"LVDSOUT{f + 1}" for f in range(2)]
        return ttl_outs + lvds_outs


# @pydanticdataclass
class ExperimentLoader(BaseModel):
    """
    The stores multiple Profiles and can be used in the GUI.
    The is analoaghous to the information shown in the legacy
    ncd_detectors configuration GUI in GDA
    These can be stored as yaml files or as objects and used for experiments
    """

    profiles: list[Profile]
    instrument: str
    detectors: list[Any]
    instrument_session: str = ""

    @property
    def n_profiles(self):
        return len(self.profiles)

    @classmethod
    def read_from_yaml(cls, config_filepath: str | Path):
        """Reads an Experimental configuration, containing n profiles
        and generates a ExperimentalProfiles object"""
        with open(config_filepath) as file:
            try:
                model_dict = yaml.safe_load(file)
            except yaml.YAMLError as e:
                raise e

            model: ExperimentLoader = ExperimentLoader.model_validate(model_dict)

            return cls(
                profiles=model.profiles,
                instrument=model.instrument,
                detectors=model.detectors,
                instrument_session=model.instrument_session,
            )

    def save_to_yaml(self, filepath: str | Path):
        print("Saving configuration to:", filepath)

        config_dict = self.model_dump()

        with open(filepath, "w") as outfile:
            yaml.dump(
                config_dict,
                outfile,
                default_flow_style=None,
                sort_keys=False,
                indent=2,
                explicit_start=True,
            )

    def delete_profile(self, n: int):
        """Deletes the nth profile from the object"""
        self.profiles.pop(n)

    def append_profile(self, profile: Profile):
        self.profiles.append(deepcopy(profile))
