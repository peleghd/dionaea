#!/opt/dionaea/bin/python3.1

from optparse import OptionParser
import sqlite3
import json
import sys

def resolve_result(resultcursor):
	names = [resultcursor.description[x][0] for x in range(len(resultcursor.description))]
	resolvedresult = [ dict(zip(names, i)) for i in resultcursor]
	return resolvedresult

def print_offers(cursor, connection, indent):
	r = cursor.execute("SELECT * from offers WHERE connection = ?", (connection, ))
	offers = resolve_result(r)
	for offer in offers:
		print("{:s} offer: {:s}".format(' ' * indent, offer['offer_url']))

def print_downloads(cursor, connection, indent):
	r = cursor.execute("SELECT * from downloads WHERE connection = ?", (connection, ))
	downloads = resolve_result(r)
	for download in downloads:
		print("{:s} download: {:s} {:s}".format(
			' ' * indent, download['download_md5_hash'],
			download['download_url']))
	
def print_profiles(cursor, connection, indent):
	r = cursor.execute("SELECT * from emu_profiles WHERE connection = ?", (connection, ))
	profiles = resolve_result(r)
	for profile in profiles:
		print("{:s} profile: {:s}".format(
			' ' * indent, json.loads(profile['emu_profile_json'])))
		
def print_services(cursor, connection, indent):
	r = cursor.execute("SELECT * from emu_services WHERE connection = ?", (connection, ))
	services = resolve_result(r)
	for service in services:
		print("{:s} service: {:s}".format(
			' ' * intent, service['emu_service_url']))

def print_p0fs(cursor, connection, indent):
	r = cursor.execute("SELECT * from p0fs WHERE connection = ?", (connection, ))
	p0fs = resolve_result(r)
	for p0f in p0fs:
		print("{:s} p0f: genre:'{:s}' detail:'{:s}' uptime:'{:s}' tos:'{:s}' dist:'{:d}' nat:'{:d}' fw:'{:d}'".format(
			' ' * indent, p0f['p0f_genre'], p0f['p0f_detail'],
			p0f['p0f_uptime'], p0f['p0f_tos'], p0f['p0f_dist'], p0f['p0f_nat'],
			p0f['p0f_fw'])) 

def print_dcerpcbinds(cursor, connection, indent):
	r = cursor.execute("""
		SELECT DISTINCT
			dcerpcbind_uuid,
			dcerpcservice_name,
			dcerpcbind_transfersyntax
		FROM
			dcerpcbinds 
			LEFT OUTER JOIN dcerpcservices ON (dcerpcbind_uuid = dcerpcservice_uuid)
		WHERE 
			connection = ?""", (connection, ))
	dcerpcbinds = resolve_result(r)
	for dcerpcbind in dcerpcbinds:
		print("{:s} dcerpc bind: uuid '{:s}' ({:s}) transfersyntax {:s}".format(
			' ' * indent,
			dcerpcbind['dcerpcbind_uuid'], 
			dcerpcbind['dcerpcservice_name'],
			dcerpcbind['dcerpcbind_transfersyntax']) )


def print_dcerpcrequests(cursor, connection, indent):
	r = cursor.execute("""
		SELECT 
			dcerpcrequest_uuid,
			dcerpcservice_name,
			dcerpcrequest_opnum,
			dcerpcserviceop_name,
			dcerpcserviceop_vuln
		FROM 
			dcerpcrequests 
			LEFT OUTER JOIN dcerpcservices ON (dcerpcrequest_uuid = dcerpcservice_uuid) 
			LEFT OUTER JOIN dcerpcserviceops ON (dcerpcservices.dcerpcservice = dcerpcserviceops.dcerpcservice AND dcerpcrequest_opnum = dcerpcserviceop_opnum)
		WHERE 
			connection = ?""", (connection, ))
	dcerpcrequests = resolve_result(r)
	for dcerpcrequest in dcerpcrequests:
		print("{:s} dcerpc request: uuid '{:s}' ({:s}) opnum {:d} ({:s} ({:s}))".format(
			' ' * indent,
			dcerpcrequest['dcerpcrequest_uuid'], 
			dcerpcrequest['dcerpcservice_name'], 
			dcerpcrequest['dcerpcrequest_opnum'], 
			dcerpcrequest['dcerpcserviceop_name'], 
			dcerpcrequest['dcerpcserviceop_vuln']) )

def print_siprequest(cursor, connection, indent):
	pass

def print_sipresponse(cursor, connection, indent):
	pass

def print_rtpstream(cursor, connection, indent):
	pass

def print_connection(c, indent):
	indentStr = ' ' * (indent + 1)

	if c['connection_type'] in ['accept', 'reject', 'pending']:
		print(indentStr + 'connection {:d} {:s} {:s} {:s} {:s}:{:d} <- {:s}:{:d}'.format(
			c['connection'], c['connection_protocol'], c['connection_transport'],
			c['connection_type'], c['local_host'], c['local_port'],
			c['remote_host'], c['remote_port']), end='')
	elif c['connection_type'] == 'connect':
		print(indentStr + 'connection {:d} {:s} {:s} {:s} {:s}:{:d} -> {:s}/{:s}:{:d}'.format(
			c['connection'], c['connection_protocol'],
			c['connection_transport'], c['connection_type'], c['local_host'],
			c['local_port'], c['remote_hostname'], c['remote_host'],
			c['remote_port']), end='')
	elif c['connection_type'] == 'listen':
		print(indentStr + 'connection {:d} {:s} {:s} {:s} {:s}:{:d}'.format(
			c['connection'], c['connection_protocol'],
			c['connection_transport'], c['connection_type'], c['local_host'],
			c['local_port']), end='')

	print(' ({:d} {:s})'.format(c['connection_root'], c['connection_parent']))

def recursive_print(cursor, connection, indent):
	result = cursor.execute("SELECT * from connections WHERE connection_parent = ?", (connection, ))
	connections = resolve_result(result)
	for c in connections:
		if c['connection'] == connection:
			continue
		print_connection(c, indent)
		print_p0fs(cursor, c['connection'], indent+2)
		print_offers(cursor, c['connection'], indent+2)
		print_downloads(cursor, c['connection'], indent+2)
		recursive_print(cursor, c['connection'], indent+2)
		

def print_db(opts, args):
	dbh = sqlite3.connect(args[0])
	cursor = dbh.cursor()

	offset = 0
	limit = 1000

	query = """
SELECT DISTINCT 
	c.connection AS connection,
	connection_root,
	connection_parent,
	connection_type,
	connection_protocol,
	connection_transport,
    datetime(connection_timestamp, 'unixepoch') AS connection_timestamp,
	local_host,
	local_port,
	remote_host,
	remote_hostname,
	remote_port 
FROM 
	connections AS c
	LEFT OUTER JOIN offers ON (offers.connection = c.connection)
	LEFT OUTER JOIN downloads ON (downloads.connection = c.connection)
	LEFT OUTER JOIN dcerpcbinds ON (dcerpcbinds.connection = c.connection)
	LEFT OUTER JOIN dcerpcrequests ON (dcerpcrequests.connection = c.connection)
WHERE
	(c.connection_root = c.connection OR c.connection_root IS NULL)
"""

	if options.remote_host:
		query = query + "\tAND remote_host = {:s} \n".format(options.remote_host)

	if options.connection:
		query = query + "\tAND c.connection = {:d} \n".format(options.connection)
	
	if options.in_offer_url:
		query = query + "\tAND offer_url LIKE '%{:s}%' \n".format(options.in_offer_url)

	if options.in_download_url:
		query = query + "\tAND download_url LIKE '%{:s}%' \n".format(options.in_download_url)

	if options.time_from:
		query = query + "\tAND connection_timestamp > {:s} \n".format(options.time_from)

	if options.time_to:
		query = query + "\tAND connection_timestamp < {:s} \n".format(options.time_to)

	if options.uuid:
		query = query + "\tAND dcerpcbind_uuid = '{:s}' \n".format(options.uuid)

	if options.opnum:
		query = query + "\tAND dcerpcrequest_opnum = {:s} \n".format(options.opnum)
			
	if options.protocol:
		query = query + "\tAND connection_protocol = '{:s}' \n".format(options.protocol)
					
	if options.md5sum:
		query = query + "\tAND download_md5_hash = '{:s}' \n".format(options.md5sum)
	
	if options.type:
		query = query + "\tAND connection_type = '{:s}' \n".format(options.type)

	if options.query:
		print(query)
		return
			
	while True:
		lquery = query + "\t LIMIT {:d} OFFSET {:d} \n".format(limit, offset)
		result = cursor.execute(lquery)
		connections = resolve_result(result)
#		print(connections)	
		for c in connections:
			connection = c['connection']
			print("{:s}".format(c['connection_timestamp']))
			print_connection(c, 1)
			print_p0fs(cursor, c['connection'], 2)
			print_dcerpcbinds(cursor, c['connection'], 2)
			print_dcerpcrequests(cursor, c['connection'], 2)
			print_profiles(cursor, c['connection'], 2)
			print_offers(cursor, c['connection'], 2)
			print_downloads(cursor, c['connection'], 2)
			print_services(cursor, c['connection'], 2)
			recursive_print(cursor, c['connection'], 2)

		offset += limit
		if len(connections) != limit:
			break

if __name__ == "__main__":
	parser = OptionParser()
	parser.add_option("-r", "--remote-host", action="store", type="string", dest="remote_host")
	parser.add_option("-o", "--in-offer-url", action="store", type="string", dest="in_offer_url")
	parser.add_option("-d", "--in-download-url", action="store", type="string", dest="in_download_url")
	parser.add_option("-c", "--connection", action="store", type="int", dest="connection")
	parser.add_option("-q", "--query-only", action="store_true", dest="query", default=False)
	parser.add_option("-t", "--time-from", action="store", type="string", dest="time_from")
	parser.add_option("-T", "--time-to", action="store", type="string", dest="time_to")
	parser.add_option("-u", "--dcerpcbind-uuid", action="store", type="string", dest="uuid")
	parser.add_option("-p", "--dcerpcrequest-opnum", action="store", type="string", dest="opnum")
	parser.add_option("-P", "--protocol", action="store", type="string", dest="protocol")
	parser.add_option("-m", "--downloads-md5sum", action="store", type="string", dest="md5sum")
	parser.add_option("-y", "--connection-type", action="store", type="string", dest="type")
	(options, args) = parser.parse_args()
	print_db(options, args)
