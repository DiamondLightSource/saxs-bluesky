import os, copy, yaml
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from ophyd_async.fastcs.panda import (
	SeqTable,
	SeqTrigger)

from ophyd_async.core import in_micros #DetectorTrigger, TriggerInfo, wait_for_value, 
# from ophyd_async.plan_stubs import store_settings

# import bluesky.plan_stubs as bps
# from bluesky import RunEngine
# from dodal.beamlines.i22 import panda1

from pydantic import BaseModel
from pydantic_core import from_json
from pydantic.dataclasses import dataclass
from typing import List, Any

from utils.ncdcore import ncdcore


"""

Note to self:

HDFPanda:
	pulse
	seq
	pcomp
	pcap
	data
	inenc


"""

"""

Group and Profile BaseModels

"""


time_units = {"ns": 1e-9, "nsec": 1e-9, "usec": 1e-6, "ms": 1e-3, "msec": 1e-3,
	"s": 1, "sec": 1, "min": 60, "m": 60, "hour": 60*60, "h": 60*60 }


class Group(BaseModel):

	frames: int
	wait_time: int
	wait_units: str
	run_time: int
	run_units: str
	pause_trigger: str
	wait_pulses: List[int] #0 or 1 only
	run_pulses: List[int] #0 or 1 only
	
	#created by model_post_init
	wait_time_s: float = None
	run_time_s: float = None
	group_duration: float = None


	def model_post_init(self, __context: Any) -> None:

		self.run_units = self.run_units.upper()
		self.wait_units = self.wait_units.upper()
		self.pause_trigger = self.pause_trigger.upper()
		self.recalc_times()

	def recalc_times(self):
		
		self.wait_time_s = self.wait_time*ncdcore.to_seconds(self.wait_units)
		self.run_time_s = self.run_time*ncdcore.to_seconds(self.run_units)
		self.group_duration = (self.wait_time_s+self.run_time_s)*self.frames

	
	def seq_row(self):

		self.recalc_times()

		if not self.pause_trigger:
			trigger = SeqTrigger.IMMEDIATE

		if self.pause_trigger:
			trigger = eval(f"SeqTrigger.{self.pause_trigger}")

		seq_row  = SeqTable.row(
			repeats = self.frames,
			trigger = trigger,
			position = 0,
			time1 = in_micros(self.wait_time_s),
			outa1 = self.wait_pulses[0],
			outb1 = self.wait_pulses[1],
			outc1 = self.wait_pulses[2],
			outd1 = self.wait_pulses[3],
			# oute1 = self.wait_pulses[4],
			# outf1 = self.wait_pulses[5],
			time2 = in_micros(self.run_time_s),
			outa2 = self.run_pulses[0],
			outb2 = self.run_pulses[1],
			outc2 = self.run_pulses[2],
			outd2 = self.run_pulses[3],
			# oute2 = self.run_pulses[4],
			# outf2 = self.run_pulses[5],
		)

		return seq_row



class Profile(BaseModel):
	
	profile_id: int = 0
	cycles: int = 1
	seq_trigger: str = "IMMEDIATE"
	groups: List[Group] = []
	multiplier: List[int] = [1, 1, 1, 1]

	total_frames: int = 0
	duration_per_cycle: float = 0

	def model_post_init(self, __context: Any):
		
		if len(self.groups) > 0:

			self.analyse_profile()

	# def re_group_id_groups(self):
		
	# 	iter_group = copy.deepcopy(self.groups)
	# 	new_groups = []

	# 	for n, group in enumerate(iter_group):
	# 		group.group_id = n
	# 		new_groups.append(group)

	# 	self.groups = new_groups

	# 	[f.recalc_times() for f in self.groups]

	def analyse_profile(self):

		self.calc_total_frames()
		self.calc_duration_per_cycle()



	def calc_total_frames(self):

		self.total_frames = 0
		for n_group in self.groups:
			self.total_frames+=n_group.frames
		return self.total_frames
	
	def calc_duration_per_cycle(self):

		self.duration_per_cycle = 0

		for n_group in self.groups:
			self.duration_per_cycle+=n_group.group_duration
		return self.duration_per_cycle
	
	@property
	def duration(self):
		duration = self.duration_per_cycle*self.cycles
		return duration
	
	@property
	def active_out(self):

		wait_matrix = np.array([g.wait_pulses for g in self.groups])
		run_matrix = np.array([g.run_pulses for g in self.groups])
		active_matrix = wait_matrix+run_matrix
		active_out = np.where((np.sum(active_matrix,axis=0)) != 0)[0]

		return active_out


	def analyse_profile_legacy(self):

		self.wait_matrix = []	
		self.run_matrix = []
		self.duration = 0
		self.duration_per_cycle = 0
		self.total_frames = 0

		for n_group in self.groups:

			self.duration_per_cycle+=n_group.group_duration
			self.total_frames+=n_group.frames

			self.wait_matrix.append(n_group.wait_pulses)
			self.run_matrix.append(n_group.run_pulses)
		
		self.duration=self.duration_per_cycle*self.cycles

		self.wait_matrix = np.asarray(self.wait_matrix)
		self.run_matrix = np.asarray(self.run_matrix)

		self.n_groups = len(self.groups)
		self.veto_trigger_time, self.veto_signal, self.active_out = self.build_veto_signal()

		close_list = [np.abs(1-np.log10(np.amin((np.asarray(self.veto_trigger_time[self.veto_trigger_time!=0])/time_units[i])))) for i in time_units.keys()]
		self.best_time_unit = list(time_units)[np.argmin(close_list)]


	def append_group(self, Group, analyse_profile=True):

		self.groups.append(Group)
		# self.re_group_id_groups()

		if analyse_profile:
			self.analyse_profile()

	
	def delete_group(self, id, analyse_profile=True):

		self.groups.pop(id)
		# self.re_group_id_groups()

		if analyse_profile:
			self.analyse_profile()

	def insert_group(self, id, Group, analyse_profile=True):

		self.groups.insert(id, Group)
		# self.re_group_id_groups()

		
		if analyse_profile:
			self.analyse_profile()
			
	
	# def load_profile_to_panda(self, panda):
		
	# 	table = self.seq_table()
			
	# 	yield from bps.abs_set(panda.seq[1].table, table, group="panda-config")



	def build_veto_signal(self):

		trigger_time = [0]
		veto_signal = [0] #starts low and ends low
		current_time = 0 

		profile_wait_matrix = self.wait_matrix
		profile_run_matrix = self.run_matrix

		active_matrix = profile_wait_matrix+profile_run_matrix
		active_out = np.where((np.sum(active_matrix,axis=0)) != 0)[0]

		# active_wait_matrix = profile_wait_matrix[:,active_out]
		# active_run_matrix = profile_run_matrix[:,active_out]


		for g in range(self.n_groups):
			group = self.groups[g]

			group.group_duration

			veto_active = np.sum(profile_run_matrix[g,:])

			for f in range(group.frames):

				###wait phase

				current_time += group.wait_time*ncdcore.to_seconds(group.wait_units)
				trigger_time.append(current_time)
				veto_signal.append(0)
 
				#run phase

				current_time += group.run_time*ncdcore.to_seconds(group.run_units)
				trigger_time.append(current_time)
				
				if veto_active != 0:
					veto_signal.append(1)
				else:
					veto_signal.append(0)


		trigger_time.append(current_time+(current_time)/10)
		veto_signal.append(0)  #starts low and ends low

		self.trigger_time = np.asarray(trigger_time)
		self.veto_signal = np.asarray(veto_signal)
		self.active_out = active_out

		return np.asarray(trigger_time), np.asarray(veto_signal), active_out

	def build_usr_signal(self,usr):

		trigger_time = [-1*time_units[self.best_time_unit]]
		usr_signal = [0] #starts low and ends low

		trigger_time.append(0)
		usr_signal.append(0) #starts low and ends low
		current_time = 0 

		for g in range(self.n_groups):
			group = self.groups[g]

			usr_run_active = group.run_pulses[usr]
			usr_wait_active = group.wait_pulses[usr]
			usr_active = usr_run_active+usr_wait_active

			for f in range(group.frames):

				###wait phase

				current_time += group.wait_time*ncdcore.to_seconds(group.wait_units)
				trigger_time.append(current_time)

				if (usr_active!=0):
					usr_signal.append(1)
				else:
					usr_signal.append(0)
 
				#run phase

				current_time += group.run_time*ncdcore.to_seconds(group.run_units)
				trigger_time.append(current_time)
				
				if usr_run_active != 0:
					usr_signal.append(1)
				else:
					usr_signal.append(0)

		trigger_time.append(current_time+(current_time)/10)
		usr_signal.append(0)  #starts low and ends low

		self.trigger_time = np.asarray(trigger_time)
		self.usr_signal = np.asarray(usr_signal)

		return np.asarray(trigger_time), np.asarray(usr_signal)


	def plot_triggering(self,blocking=True):


		self.veto_trigger_time, self.veto_signal, self.active_out = self.build_veto_signal()
		
		print("plotting in:", self.best_time_unit)

		figure, axes = plt.subplots(len(self.active_out)+1, 1,sharex=True,figsize=(10,len(self.active_out)*4))

		if len(self.active_out) > 0:

			axes[0].step(self.veto_trigger_time/time_units[self.best_time_unit],self.veto_signal)
			axes[0].set_ylabel("Veto Signal")

			for u in range(len(self.active_out)):
				usr_trigger_time, usr_signal = self.build_usr_signal(u)
				axes[u+1].step(usr_trigger_time/time_units[self.best_time_unit],usr_signal)
				axes[u+1].set_ylabel(f"Usr{u} Signal")
				
			plt.xlabel(f"Time ({self.best_time_unit})")
			plt.show(block=blocking)

		else:

			print("None active in this profile")

	def seq_table(self):

		table = SeqTable()

		[table := table + group.seq_row() for group in self.groups]

		return table
	
	@staticmethod
	def inputs():

		TTLINS = ["TTLIN"+str(f+1) for f in range(6)]
		LVDSINS = ["LVDSIN"+str(f+1) for f in range(2)]

		return TTLINS + LVDSINS
	
	@staticmethod
	def seq_triggers():

		return list(SeqTrigger.__dict__["_member_names_"])
	

	@staticmethod
	def outputs():

		TTLOUTS = ["TTLOUT"+str(f+1) for f in range(10)]
		LVDSOUTS = ["LVDSOUT"+str(f+1) for f in range(2)]

		return TTLOUTS + LVDSOUTS

	

@dataclass #pydantic dataclass
class ProfileLoader():

	profiles: List[Profile]
	instrument: str
	experiment: str
	detectors: List[str]

	def __post_init__(self):

		try:
			self.data_dir = os.path.join("/dls",self.instrument,"data",str(self.year),self.experiment)
		except:
			pass
		
		self.n_profiles = len(self.profiles)

	@staticmethod
	def read_from_yaml(config_filepath):

		with open(config_filepath, 'rb') as file:
			print("Using config:",config_filepath)

			if config_filepath.endswith('.yaml') or config_filepath.endswith('.yml'):
				try:
					config = yaml.full_load(file)
				except TypeError:
					print("Must be a yaml file")
			
			if not os.path.exists(config_filepath):
				raise FileNotFoundError(f"Cannot find file: {config_filepath}")

		
			instrument = config["instrument"]
			experiment = config["experiment"]
			detectors = config["detectors"]

			if "year" not in config:
				year = datetime.now().year
			else:
				year = config["year"]


			profile_names = [f for f in config if f.startswith("profile")]
			profiles = []

			for p,profile_name in enumerate(profile_names):

				profile_cycles = config[profile_name]["cycles"]
				profile_trigger = config[profile_name]["seq_trigger"]
				multiplier = config[profile_name]["multiplier"]
				groups = {key: config[profile_name][key] for key in config[profile_name].keys() if key.startswith("group")}
				group_list = []

				for g,group_name in enumerate(groups.keys()):

					group = config[profile_name][group_name]

					n_Group  = Group(frames=group["frames"], 
									wait_time=group["wait_time"], 
									wait_units=group["wait_units"], 
									run_time=group["run_time"], 
									run_units=group["run_units"],
									pause_trigger=group["pause_trigger"], 
									wait_pulses=group["wait_pulses"], 
									run_pulses=group["run_pulses"])
					
					group_list.append(n_Group)

				n_profile = Profile(profile_id=p, 
						cycles=profile_cycles, 
						seq_trigger=profile_trigger, 
						groups=group_list, 
						multiplier=multiplier)

				profiles.append(n_profile)

			self = ProfileLoader(profiles, instrument, experiment, detectors)

			return self
		
	
	def to_dict(self) -> dict:

		exp_dict = {"title": "Panda Configure",
					"experiment": self.experiment, 
					"instrument": self.instrument,
					"detectors": self.detectors}


		for p,profile in enumerate(self.profiles):

			profile_dict = profile.model_dump()
			del profile_dict["groups"]

			for g,group in enumerate(profile.groups):
				group_dict = group.model_dump()
				profile_dict["group-"+str(g)] = group_dict

			exp_dict["profile-"+str(p)] = profile_dict
		
		return exp_dict

		
	def save_to_yaml(self, filepath: str):

		print("Saving configuration to:",filepath)

		config_dict  = self.to_dict()
		
		with open(filepath, 'w') as outfile:
			yaml.dump(config_dict, outfile, default_flow_style=None, sort_keys=False, indent=2, explicit_start=True)

	
	def delete_profile(self, n):

		self.profiles.pop(n)
		# self.re_group_id_profiles()
		self.__post_init__()

	def append_profile(self, Profile):

		self.profiles.append(Profile)
		# self.re_group_id_profiles()
		self.__post_init__()

	def re_group_id_profiles(self):
		
		iter_prof = copy.deepcopy(self.profiles)
		new_profiles = []

		for n, profile in enumerate(iter_prof):
			profile.profile_id = n
			new_profiles.append(profile)

		self.profiles = new_profiles


# def savei22pandaconfig(output_file):

# 	# i22panda = panda1()
# 	# save_device(i22panda)

#     _save_panda("i22", "panda1", output_file)



# def load_panda(config_yaml_path):

# 	config_yaml_path = config_yaml_path

# 	def _load(config_yaml_path):
# 		i22panda = panda1()
# 		yield from load_device(i22panda, str(config_yaml_path))

# 	RE = RunEngine({})
# 	RE(_load())



if __name__ == "__main__":
	
	P = Profile()
	P.append_group(Group(frames=1, wait_time=1, wait_units="S", run_time=1, run_units="S", pause_trigger="False", wait_pulses=[0,0,0,0], run_pulses=[1,1,1,1]))

	json_schema = P.model_dump_json()
    

	profile = Profile.model_validate(P)
	
	new_profile = Profile.model_validate(from_json(json_schema, allow_partial=True))

	print(new_profile)

	quit()

	dir_path = os.path.dirname(os.path.realpath(__file__))
	config_filepath = os.path.join(dir_path,"panda_config.yaml")


	config = PandaTriggerConfig.read_from_yaml(config_filepath)
	config.save_to_yaml(os.path.join(dir_path,"panda_config_output.yaml"))
	
	


	#     yield from bps.abs_set(
    #     panda.inenc[1].setp,  # type: ignore
    #     initial_x * MM_TO_ENCODER_COUNTS,
    #     wait=True,
    # )

	    # yield from bps.abs_set(panda.pulse[1].wgroup_idth, exposure_time_s, group="panda-config")


    # table = _get_seq_table(parameters, exposure_distance_mm, time_between_x_steps_ms)

    # yield from bps.abs_set(panda.seq[1].table, table, group="panda-config")

    # yield from bps.abs_set(
    #     panda.pcap.enable,  # type: ignore
    #     Enabled.ENABLED.value,
    #     group="panda-config",
    # )


# def arm_panda_for_grgroup_idscan(panda: HDFPanda, group="arm_panda_grgroup_idscan"):
#     yield from bps.abs_set(panda.seq[1].enable, Enabled.ENABLED.value, group=group)  # type: ignore
#     yield from bps.abs_set(panda.pulse[1].enable, Enabled.ENABLED.value, group=group)  # type: ignore
#     yield from bps.abs_set(panda.counter[1].enable, Enabled.ENABLED.value, group=group)  # type: ignore
#     yield from bps.abs_set(panda.pcap.arm, PcapArm.ARMED.value, group=group)  # type: ignore
#     yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)
#     LOGGER.info("PandA has been armed")


# def disarm_panda_for_grgroup_idscan(panda, group="disarm_panda_grgroup_idscan") -> MsgGenerator:
#     yield from bps.abs_set(panda.pcap.arm, PcapArm.DISARMED.value, group=group)  # type: ignore
#     yield from bps.abs_set(panda.counter[1].enable, Enabled.DISABLED.value, group=group)  # type: ignore
#     yield from bps.abs_set(panda.seq[1].enable, Enabled.DISABLED.value, group=group)
#     yield from bps.abs_set(panda.pulse[1].enable, Enabled.DISABLED.value, group=group)
#     yield from bps.abs_set(panda.pcap.enable, Enabled.DISABLED.value, group=group)  # type: ignore
#     yield from bps.wait(group=group, timeout=GENERAL_TIMEOUT)
