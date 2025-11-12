# for localized messages
from . import _

import codecs
import re
import six
from shutil import copy2
from time import localtime, time, strftime

from enigma import eDVBDB, eDVBFrontendParametersSatellite

from Components.ActionMap import ActionMap
from Components.config import ConfigText, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import fileCheck

debug_name = "LamedbMerger"
lamedb_path = "/etc/enigma2"

class LamedbReader():
	def readLamedb(self, path, transponders=None):
		#print("[%s-LamedbReader] Reading lamedb... %s" % (debug_name, path))

		if not isinstance(transponders, dict):
			transponders = {}

		lamedb = open(path + "/lamedb", "r")
		content = lamedb.read()
		lamedb.close()

		lamedb_ver = 4
		result = re.match('eDVB services /([45])/', content)
		if result:
			lamedb_ver = int(result.group(1))
			#print("[%s-LamedbReader] lamedb ver" % (debug_name), lamedb_ver)
		if lamedb_ver == 4:
			transponders = self.parseLamedbV4Content(content, transponders)
		elif lamedb_ver == 5:
			transponders = self.parseLamedbV5Content(content, transponders)
		return transponders

	def parseLamedbV4Content(self, content, transponders):
		transponders_count = 0
		services_count = 0

		tp_start = content.find("transponders\n")
		tp_stop = content.find("end\n")
		
		if tp_start < 0 or tp_stop < 0:
			print("[%s-LamedbReader] parseLamedbV4Content: no transponders found" % (debug_name))
			return transponders

		tp_blocks = content[tp_start + 13:tp_stop].strip().split("/")
		content = content[tp_stop + 4:]

		for block in tp_blocks:
			rows = block.strip().split("\n")
			if len(rows) != 2:
				continue

			first_row = rows[0].strip().split(":")
			if len(first_row) != 3:
				continue

			transponder = {}
			transponder["services"] = {}
			transponder["namespace"] = int(first_row[0], 16)
			transponder["transport_stream_id"] = int(first_row[1], 16)
			transponder["original_network_id"] = int(first_row[2], 16)

			#print("%x:%x:%x" % (namespace, transport_stream_id, original_network_id))
			second_row = rows[1].strip()
			transponder["dvb_type"] = 'dvb' + second_row[0]
			if transponder["dvb_type"] not in ["dvbs", "dvbt", "dvbc"]:
				continue

			second_row = second_row[2:].split(":")
			
			if not all(second_row): # empty fields are not valid
				continue

			if transponder["dvb_type"] == "dvbs" and len(second_row) not in (7, 11, 14, 16):
				continue
			if transponder["dvb_type"] == "dvbt" and len(second_row) != 12:
				continue
			if transponder["dvb_type"] == "dvbc" and len(second_row) != 7:
				continue

			if transponder["dvb_type"] == "dvbs":
				transponder["frequency"] = int(second_row[0])
				transponder["symbol_rate"] = int(second_row[1])
				transponder["polarization"] = int(second_row[2])
				transponder["fec_inner"] = int(second_row[3])
				orbital_position = int(second_row[4])
				if orbital_position < 0:
					transponder["orbital_position"] = orbital_position + 3600
				else:
					transponder["orbital_position"] = orbital_position

				transponder["inversion"] = int(second_row[5])
				transponder["flags"] = int(second_row[6])
				if len(second_row) == 7: # DVB-S
					transponder["system"] = 0
				else: # DVB-S2
					transponder["system"] = int(second_row[7])
					transponder["modulation"] = int(second_row[8])
					transponder["roll_off"] = int(second_row[9])
					transponder["pilot"] = int(second_row[10])
					if len(second_row) > 13: # Multistream
						transponder["is_id"] = int(second_row[11])
						transponder["pls_code"] = int(second_row[12])
						transponder["pls_mode"] = int(second_row[13])
						if len(second_row) > 15: # T2MI
							transponder["t2mi_plp_id"] = int(second_row[14])
							transponder["t2mi_pid"] = int(second_row[15])
			elif transponder["dvb_type"] == "dvbt":
				transponder["frequency"] = int(second_row[0])
				transponder["bandwidth"] = int(second_row[1])
				transponder["code_rate_hp"] = int(second_row[2])
				transponder["code_rate_lp"] = int(second_row[3])
				transponder["modulation"] = int(second_row[4])
				transponder["transmission_mode"] = int(second_row[5])
				transponder["guard_interval"] = int(second_row[6])
				transponder["hierarchy"] = int(second_row[7])
				transponder["inversion"] = int(second_row[8])
				transponder["flags"] = int(second_row[9])
				transponder["system"] = int(second_row[10])
				transponder["plpid"] = int(second_row[11])
			elif transponder["dvb_type"] == "dvbc":
				transponder["frequency"] = int(second_row[0])
				transponder["symbol_rate"] = int(second_row[1])
				transponder["inversion"] = int(second_row[2])
				transponder["modulation"] = int(second_row[3])
				transponder["fec_inner"] = int(second_row[4])
				transponder["flags"] = int(second_row[5])
				transponder["system"] = int(second_row[6])

			key = "%x:%x:%x" % (transponder["namespace"], transponder["transport_stream_id"], transponder["original_network_id"])
			if not key in transponders:
				transponders[key] = transponder
				transponders_count += 1

		srv_start = content.find("services\n")
		srv_stop = content.rfind("end\n")

		if srv_start < 0 or srv_stop < 0:
			print("[%s-LamedbReader] parseLamedbV4Content: no services found" % (debug_name))
			return transponders

		srv_blocks = content[srv_start + 9:srv_stop].strip().split("\n")

		for i in range(0, len(srv_blocks) // 3):
			service_reference = srv_blocks[i * 3].strip()
			service_name = srv_blocks[(i * 3) + 1].strip()
			service_provider = srv_blocks[(i * 3) + 2].strip()
			service_reference = service_reference.split(":")

			if len(service_reference) not in (6, 7):
				continue

			service = {}
			service["service_name"] = service_name
			service["service_line"] = service_provider
			service["service_id"] = int(service_reference[0], 16)
			service["namespace"] = int(service_reference[1], 16)
			service["transport_stream_id"] = int(service_reference[2], 16)
			service["original_network_id"] = int(service_reference[3], 16)
			service["service_type"] = int(service_reference[4])
			service["flags"] = int(service_reference[5])
			if len(service_reference) == 7 and int(service_reference[6], 16) != 0:
				service["ATSC_source_id"] = int(service_reference[6], 16)

			key = "%x:%x:%x" % (service["namespace"], service["transport_stream_id"], service["original_network_id"])
			if key not in transponders:
				continue

			# The original (correct) code
			# transponders[key]["services"][service["service_id"]] = service

			# Dirty hack to work around the (well known) service type bug in lamedb/enigma2
			transponders[key]["services"]["%x:%x" % (service["service_id"], service["service_type"])] = service

			services_count += 1

		#print("[%s-LamedbReader] Read %d transponders and %d services" % (debug_name, transponders_count, services_count))
		return transponders

	def parseLamedbV5Content(self, content, transponders):
		transponders_count = 0
		services_count = 0

		lines = content.splitlines()
		for line in lines:
			if line.startswith("t:"):
				first_part = line.strip().split(",")[0][2:].split(":")
				if len(first_part) != 3:
					continue

				transponder = {}
				transponder["services"] = {}
				transponder["namespace"] = int(first_part[0], 16)
				transponder["transport_stream_id"] = int(first_part[1], 16)
				transponder["original_network_id"] = int(first_part[2], 16)

				second_part = line.strip().split(",")[1]
				transponder["dvb_type"] = 'dvb' + second_part[0]
				if transponder["dvb_type"] not in ["dvbs", "dvbt", "dvbc"]:
					continue

				second_part = second_part[2:].split(":")

				if transponder["dvb_type"] == "dvbs" and len(second_part) not in (7, 11):
					continue
				if transponder["dvb_type"] == "dvbt" and len(second_part) != 12:
					continue
				if transponder["dvb_type"] == "dvbc" and len(second_part) != 7:
					continue

				if transponder["dvb_type"] == "dvbs":
					transponder["frequency"] = int(second_part[0])
					transponder["symbol_rate"] = int(second_part[1])
					transponder["polarization"] = int(second_part[2])
					transponder["fec_inner"] = int(second_part[3])
					orbital_position = int(second_part[4])
					if orbital_position < 0:
						transponder["orbital_position"] = orbital_position + 3600
					else:
						transponder["orbital_position"] = orbital_position

					transponder["inversion"] = int(second_part[5])
					transponder["flags"] = int(second_part[6])
					if len(second_part) == 7: # DVB-S
						transponder["system"] = 0
					else: # DVB-S2
						transponder["system"] = int(second_part[7])
						transponder["modulation"] = int(second_part[8])
						transponder["roll_off"] = int(second_part[9])
						transponder["pilot"] = int(second_part[10])
						for part in line.strip().split(",")[2:]: # Multistream/T2MI
							if part.startswith("MIS/PLS:") and len(part[8:].split(":")) == 3:
								transponder["is_id"] = int(part[8:].split(":")[0])
								transponder["pls_code"] = int(part[8:].split(":")[1])
								transponder["pls_mode"] = int(part[8:].split(":")[2])
							elif part.startswith("T2MI:") and len(part[5:].split(":")) == 2:
								transponder["t2mi_plp_id"] = int(part[5:].split(":")[0])
								transponder["t2mi_pid"] = int(part[5:].split(":")[1])
				elif transponder["dvb_type"] == "dvbt":
					transponder["frequency"] = int(second_part[0])
					transponder["bandwidth"] = int(second_part[1])
					transponder["code_rate_hp"] = int(second_part[2])
					transponder["code_rate_lp"] = int(second_part[3])
					transponder["modulation"] = int(second_part[4])
					transponder["transmission_mode"] = int(second_part[5])
					transponder["guard_interval"] = int(second_part[6])
					transponder["hierarchy"] = int(second_part[7])
					transponder["inversion"] = int(second_part[8])
					transponder["flags"] = int(second_part[9])
					transponder["system"] = int(second_part[10])
					transponder["plpid"] = int(second_part[11])
				elif transponder["dvb_type"] == "dvbc":
					transponder["frequency"] = int(second_part[0])
					transponder["symbol_rate"] = int(second_part[1])
					transponder["inversion"] = int(second_part[2])
					transponder["modulation"] = int(second_part[3])
					transponder["fec_inner"] = int(second_part[4])
					transponder["flags"] = int(second_part[5])
					transponder["system"] = int(second_part[6])

				key = "%x:%x:%x" % (transponder["namespace"], transponder["transport_stream_id"], transponder["original_network_id"])
				if not key in transponders:
					transponders[key] = transponder
					transponders_count += 1
			elif line.startswith("s:"):
				service_reference = line.strip().split(",")[0][2:]
				service_name = line.strip().split('"', 1)[1].split('"')[0]
				third_part = line.strip().split('"', 2)[2]
				service_provider = ""
				if len(third_part):
					service_provider = third_part[1:]
				service_reference = service_reference.split(":")
				if len(service_reference) != 6 and len(service_reference) != 7:
					continue

				service = {}
				service["service_name"] = service_name
				service["service_line"] = service_provider
				service["service_id"] = int(service_reference[0], 16)
				service["namespace"] = int(service_reference[1], 16)
				service["transport_stream_id"] = int(service_reference[2], 16)
				service["original_network_id"] = int(service_reference[3], 16)
				service["service_type"] = int(service_reference[4])
				service["flags"] = int(service_reference[5])
				if len(service_reference) == 7 and int(service_reference[6], 16) != 0:
					service["ATSC_source_id"] = int(service_reference[6], 16)

				key = "%x:%x:%x" % (service["namespace"], service["transport_stream_id"], service["original_network_id"])
				if key not in transponders:
					continue

				# The original (correct) code
				# transponders[key]["services"][service["service_id"]] = service

				# Dirty hack to work around the (well known) service type bug in lamedb/enigma2
				transponders[key]["services"]["%x:%x" % (service["service_id"], service["service_type"])] = service

				services_count += 1

		#print("[%s-LamedbReader] Read %d transponders and %d services" % (debug_name, transponders_count, services_count))
		return transponders


class LamedbWriter():
	def writeLamedb(self, path, transponders, filename="lamedb"):
		#print("[%s-LamedbWriter] Writing lamedb..." % (debug_name))

		transponders_count = 0
		services_count = 0

		lamedblist = []
		lamedblist.append("eDVB services /4/\n")
		lamedblist.append("transponders\n")

		for key in sorted(transponders.keys(), key=lambda x: tuple([int(n, 16) for n in x.split(":")])):
			transponder = transponders[key]
			if "services" not in transponder.keys() or len(transponder["services"]) < 1:
				continue
			lamedblist.append("%08x:%04x:%04x\n" %
				(transponder["namespace"],
				transponder["transport_stream_id"],
				transponder["original_network_id"]))

			if transponder["dvb_type"] == "dvbs":
				if transponder["orbital_position"] > 1800:
					orbital_position = transponder["orbital_position"] - 3600
				else:
					orbital_position = transponder["orbital_position"]

				if transponder["system"] == 0: # DVB-S
					lamedblist.append("\ts %d:%d:%d:%d:%d:%d:%d\n" %
						(transponder["frequency"],
						transponder["symbol_rate"],
						transponder["polarization"],
						transponder["fec_inner"],
						orbital_position,
						transponder["inversion"],
						transponder["flags"]))
				else: # DVB-S2
					multistream = ''
					t2mi = ''
					if "t2mi_plp_id" in transponder and "t2mi_pid" in transponder:
						t2mi = ':%d:%d' % (
							transponder["t2mi_plp_id"],
							transponder["t2mi_pid"])
					if "is_id" in transponder and "pls_code" in transponder and "pls_mode" in transponder:
						multistream = ':%d:%d:%d' % (
							transponder["is_id"],
							transponder["pls_code"],
							transponder["pls_mode"])
					if t2mi and not multistream: # this is to pad t2mi values if necessary.
						try: # some images are still not multistream aware after all this time
							multistream = ':%d:%d:%d' % (
								eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
								eDVBFrontendParametersSatellite.PLS_Gold,
								eDVBFrontendParametersSatellite.PLS_Default_Gold_Code)
						except AttributeError as err:
							pass #print("[%s-BouquetsWriter] some images are still not multistream aware after all this time" % (debug_name),  err)
					lamedblist.append("\ts %d:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d%s%s\n" %
						(transponder["frequency"],
						transponder["symbol_rate"],
						transponder["polarization"],
						transponder["fec_inner"],
						orbital_position,
						transponder["inversion"],
						transponder["flags"],
						transponder["system"],
						transponder["modulation"],
						transponder["roll_off"],
						transponder["pilot"],
						multistream,
						t2mi))
			elif transponder["dvb_type"] == "dvbt":
				lamedblist.append("\tt %d:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d\n" %
					(transponder["frequency"],
					transponder["bandwidth"],
					transponder["code_rate_hp"],
					transponder["code_rate_lp"],
					transponder["modulation"],
					transponder["transmission_mode"],
					transponder["guard_interval"],
					transponder["hierarchy"],
					transponder["inversion"],
					transponder["flags"],
					transponder["system"],
					transponder["plpid"]))
			elif transponder["dvb_type"] == "dvbc":
				lamedblist.append("\tc %d:%d:%d:%d:%d:%d:%d\n" %
					(transponder["frequency"],
					transponder["symbol_rate"],
					transponder["inversion"],
					transponder["modulation"],
					transponder["fec_inner"],
					transponder["flags"],
					transponder["system"]))
			lamedblist.append("/\n")
			transponders_count += 1

		lamedblist.append("end\nservices\n")
		for key in sorted(transponders.keys(), key=lambda x: tuple([int(n, 16) for n in x.split(":")])):
			transponder = transponders[key]
			if "services" not in transponder.keys():
				continue

			for key2 in sorted(transponder["services"].keys(), key=lambda x: int(x.split(":")[0], 16)):
				service = transponder["services"][key2]

				lamedblist.append("%04x:%08x:%04x:%04x:%d:%d%s\n" %
					(service["service_id"],
					service["namespace"],
					service["transport_stream_id"],
					service["original_network_id"],
					service["service_type"],
					service["flags"],
					":%x" % service["ATSC_source_id"] if "ATSC_source_id" in service else ""))

				control_chars = ''.join(list(map(six.unichr, list(range(0, 32)) + list(range(127, 160)))))
				control_char_re = re.compile('[%s]' % re.escape(control_chars))
				if 'provider_name' in service.keys():
					service_name = control_char_re.sub('', six.ensure_text(six.ensure_str(service["service_name"], encoding='latin-1'), encoding='utf-8', errors='ignore'))
					provider_name = control_char_re.sub('', six.ensure_text(six.ensure_str(service["provider_name"], encoding='latin-1'), encoding='utf-8', errors='ignore'))
				else:
					service_name = service["service_name"]

				lamedblist.append("%s\n" % service_name)

				service_ca = ""
				if "free_ca" in service.keys() and service["free_ca"] != 0:
					service_ca = ",C:0000"

				service_flags = ""
				if "service_flags" in service.keys() and service["service_flags"] > 0:
					service_flags = ",f:%x" % service["service_flags"]

				if 'service_line' in service.keys():
					lamedblist.append("%s\n" % service["service_line"])
				else:
					lamedblist.append("p:%s%s%s\n" % (provider_name, service_ca, service_flags))
				services_count += 1

		lamedblist.append("end\nHave a lot of bugs!\n")
		lamedb = codecs.open(path + "/" + filename, "w", encoding="utf-8", errors="ignore")
		lamedb.write(''.join(lamedblist))
		lamedb.close()
		del lamedblist

		#print("[%s-LamedbWriter] Wrote %d transponders and %d services" % (debug_name, transponders_count, services_count))

	def writeLamedb5(self, path, transponders, filename="lamedb5"):
		#print("[%s-LamedbWriter] Writing lamedb V5..." % (debug_name))

		transponders_count = 0
		services_count = 0

		lamedblist = []
		lamedblist.append("eDVB services /5/\n")
		lamedblist.append("# Transponders: t:dvb_namespace:transport_stream_id:original_network_id,FEPARMS\n")
		lamedblist.append("#     DVBS  FEPARMS:   s:frequency:symbol_rate:polarisation:fec:orbital_position:inversion:flags\n")
		lamedblist.append("#     DVBS2 FEPARMS:   s:frequency:symbol_rate:polarisation:fec:orbital_position:inversion:flags:system:modulation:rolloff:pilot[,MIS/PLS:is_id:pls_code:pls_mode][,T2MI:t2mi_plp_id:t2mi_pid]\n")
		lamedblist.append("#     DVBT  FEPARMS:   t:frequency:bandwidth:code_rate_HP:code_rate_LP:modulation:transmission_mode:guard_interval:hierarchy:inversion:flags:system:plp_id\n")
		lamedblist.append("#     DVBC  FEPARMS:   c:frequency:symbol_rate:inversion:modulation:fec_inner:flags:system\n")
		lamedblist.append('# Services: s:service_id:dvb_namespace:transport_stream_id:original_network_id:service_type:service_number:source_id,"service_name"[,p:provider_name][,c:cached_pid]*[,C:cached_capid]*[,f:flags]\n')

		for key in sorted(transponders.keys(), key=lambda x: tuple([int(n, 16) for n in x.split(":")])):
			transponder = transponders[key]
			if "services" not in transponder.keys() or len(transponder["services"]) < 1:
				continue
			lamedblist.append("t:%08x:%04x:%04x," %
				(transponder["namespace"],
				transponder["transport_stream_id"],
				transponder["original_network_id"]))

			if transponder["dvb_type"] == "dvbs":
				if transponder["orbital_position"] > 1800:
					orbital_position = transponder["orbital_position"] - 3600
				else:
					orbital_position = transponder["orbital_position"]

				if transponder["system"] == 0: # DVB-S
					lamedblist.append("s:%d:%d:%d:%d:%d:%d:%d\n" %
						(transponder["frequency"],
						transponder["symbol_rate"],
						transponder["polarization"],
						transponder["fec_inner"],
						orbital_position,
						transponder["inversion"],
						transponder["flags"]))
				else: # DVB-S2
					multistream = ''
					t2mi = ''
					if "is_id" in transponder and "pls_code" in transponder and "pls_mode" in transponder:
						try: # some images are still not multistream aware after all this time
							# don't write default values
							if not (transponder["is_id"] == eDVBFrontendParametersSatellite.No_Stream_Id_Filter and transponder["pls_code"] == eDVBFrontendParametersSatellite.PLS_Gold and transponder["pls_mode"] == eDVBFrontendParametersSatellite.PLS_Default_Gold_Code):
								multistream = ',MIS/PLS:%d:%d:%d' % (
									transponder["is_id"],
									transponder["pls_code"],
									transponder["pls_mode"])
						except AttributeError as err:
							pass #print("[%s-BouquetsWriter] some images are still not multistream aware after all this time" % (debug_name), err)
					if "t2mi_plp_id" in transponder and "t2mi_pid" in transponder:
						t2mi = ',T2MI:%d:%d' % (
						transponder["t2mi_plp_id"],
						transponder["t2mi_pid"])
					lamedblist.append("s:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d%s%s\n" %
						(transponder["frequency"],
						transponder["symbol_rate"],
						transponder["polarization"],
						transponder["fec_inner"],
						orbital_position,
						transponder["inversion"],
						transponder["flags"],
						transponder["system"],
						transponder["modulation"],
						transponder["roll_off"],
						transponder["pilot"],
						multistream,
						t2mi))
			elif transponder["dvb_type"] == "dvbt":
				lamedblist.append("t:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d:%d\n" %
					(transponder["frequency"],
					transponder["bandwidth"],
					transponder["code_rate_hp"],
					transponder["code_rate_lp"],
					transponder["modulation"],
					transponder["transmission_mode"],
					transponder["guard_interval"],
					transponder["hierarchy"],
					transponder["inversion"],
					transponder["flags"],
					transponder["system"],
					transponder["plpid"]))
			elif transponder["dvb_type"] == "dvbc":
				lamedblist.append("c:%d:%d:%d:%d:%d:%d:%d\n" %
					(transponder["frequency"],
					transponder["symbol_rate"],
					transponder["inversion"],
					transponder["modulation"],
					transponder["fec_inner"],
					transponder["flags"],
					transponder["system"]))
			transponders_count += 1

		for key in sorted(transponders.keys(), key=lambda x: tuple([int(n, 16) for n in x.split(":")])):
			transponder = transponders[key]
			if "services" not in transponder.keys():
				continue

			for key2 in sorted(transponder["services"].keys(), key=lambda x: int(x.split(":")[0], 16)):
				service = transponder["services"][key2]

				lamedblist.append("s:%04x:%08x:%04x:%04x:%d:%d%s," %
					(service["service_id"],
					service["namespace"],
					service["transport_stream_id"],
					service["original_network_id"],
					service["service_type"],
					service["flags"],
					":%x" % service["ATSC_source_id"] if "ATSC_source_id" in service else ":0"))

				control_chars = ''.join(list(map(six.unichr, list(range(0, 32)) + list(range(127, 160)))))
				control_char_re = re.compile('[%s]' % re.escape(control_chars))
				if 'provider_name' in service.keys():
					service_name = control_char_re.sub('', six.ensure_text(six.ensure_str(service["service_name"], encoding='latin-1'), encoding='utf-8', errors='ignore'))
					provider_name = control_char_re.sub('', six.ensure_text(six.ensure_str(service["provider_name"], encoding='latin-1'), encoding='utf-8', errors='ignore'))
				else:
					service_name = service["service_name"]

				lamedblist.append('"%s"' % service_name)

				service_ca = ""
				if "free_ca" in service.keys() and service["free_ca"] != 0:
					service_ca = ",C:0000"

				service_flags = ""
				if "service_flags" in service.keys() and service["service_flags"] > 0:
					service_flags = ",f:%x" % service["service_flags"]

				if 'service_line' in service.keys(): # from lamedb
					if len(service["service_line"]):
						lamedblist.append(",%s\n" % service["service_line"])
					else:
						lamedblist.append("\n")
				else: # from scanner
					lamedblist.append(",p:%s%s%s\n" % (provider_name, service_ca, service_flags))
				services_count += 1

		lamedb = codecs.open(path + "/" + filename, "w", encoding="utf-8", errors="ignore")
		lamedb.write(''.join(lamedblist))
		lamedb.close()
		del lamedblist

		#print("[%s-LamedbWriter] Wrote %d transponders and %d services" % (debug_name, transponders_count, services_count))


class LamedbMerger(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.title = _("LamedbMerger")
		self.skinName = ["LamedbMerger", "Setup"]
		self_checkMsg = _("Check file exists")
		self["key_green"] = StaticText(self_checkMsg)
		self["key_red"] = StaticText(_("Cancel"))
		self["description"] = StaticText()
		self.tmpfile_path = ConfigText(default="/tmp/", fixed_size=False)
		self.list = [
			getConfigListEntry(_("Location"), self.tmpfile_path, _("Location of the lamedb file to merge into %s/lamedb.") % lamedb_path),
			]
		ConfigListScreen.__init__(self, self.list)
		self["actions"] = ActionMap(["SetupActions"],
		{
			"save": self.keySave,
			"cancel": self.keyCancel,
		}, -3)

	def keyCancel(self):
		self.close()

	def keySave(self):
		if self.tmpfile_path.value.endswith("/"):
			self.tmpfile_path.value = self.tmpfile_path.value[:-1]
		filename = self.tmpfile_path.value + "/lamedb"
		if filename == fileCheck(filename):
			self.session.openWithCallback(self.MergeCallback, MessageBox, _("File found '%s'\nMerge into system lamedb now?") % filename, MessageBox.TYPE_YESNO)
		else:
			self.session.open(MessageBox, _("File '%s' could not be found.\nPlease check you have sent it to the correct folder.") % filename, MessageBox.TYPE_ERROR)
			
	def MergeCallback(self, answer):
		try:
			backupName = lamedb_path + "/lamedb-" + strftime("%Y-%m-%d_%H-%M-%S", localtime(int(time()))) +".bak"
			copy2(lamedb_path + "/lamedb", backupName) # make a backup just in case
			transponders = LamedbReader().readLamedb(path=lamedb_path) # read /etc/enigma2/lamedb
			transponders = LamedbReader().readLamedb(path=self.tmpfile_path.value, transponders=transponders) # read user lamedb
			writer = LamedbWriter()
			writer.writeLamedb(lamedb_path, transponders)
			writer.writeLamedb5(lamedb_path, transponders)
			eDVBDB.getInstance().reloadServicelist()
			msg = _("File successfully merged into '" + lamedb_path + "/lamedb'\nA backup of your previous lamedb has been stored as\n%s") % backupName
		except:
			import traceback
			traceback.print_exc()
			msg = _("Supplied lamedb could not be merged.\nCheck debug log for further details.")
		self.session.openWithCallback(self.close, MessageBox, msg, MessageBox.TYPE_INFO)


def main(session, **kwargs):
	session.open(LamedbMerger)

def Plugins(**kwargs):
	list = []

	list.append(
		PluginDescriptor(name=_("Lamedb Merger"),
		description=_("Merge lamedb files together."),
		where = [PluginDescriptor.WHERE_PLUGINMENU],
		needsRestart = False,
		fnc = main))

	return list
		
