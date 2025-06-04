

"""
	
Useful functions

"""

class ncdcore:

	@staticmethod
	def decimal_to_binary(n,bits=8): 
		"""
		(decimal_to_binary(192)
		
		gives 11000000

		"""
		binary_string =  bin(n).replace("0b", "")
		leading_zeros =  (int(bits-len(binary_string))*["0"])
		leading_zeros = "".join(leading_zeros)

		return leading_zeros+binary_string

	@staticmethod
	def binary_to_decimal(n) -> int:
		"""
		binary_to_decimal("11000000")

		gives 192

		"""
		return int(n,2)

	@staticmethod
	def str2bool(v):
		if str(v).lower() in ("y", "yes", "True", "true", "t", "1"):
			return True
		elif str(v).lower() in ("n", "no", "False", "false", "f", "0"):
			return False
		else:
			return None


	@staticmethod
	def to_seconds(unit: str) -> float:

		"""
		
		takes a unit and gives back the unit in normalised to seoncds


		eg to_seconds("msec") = 1e-3 #(in seconds)

		"""

		unit = unit.lower()

		time_units = {"ns": 1e-9, "nsec": 1e-9, "usec": 1e-6, "us": 1e-6, "ms": 1e-3, "msec": 1e-3,
			"s": 1, "sec": 1, "min": 60, "m": 60, "hour": 60*60, "h": 60*60 }

		return time_units[unit]