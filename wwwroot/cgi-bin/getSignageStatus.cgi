#! /usr/bin/ruby
#
# Created by Ron Alder on 25 Feb 2013.
# Copyright © 2013 Hughes Network Systems. All rights reserved.

# For ruby 1.9 the encoding must be set or the code may trip over multibyte characters
# in any file that it reads and parses.
if RUBY_VERSION >= "1.9"
	Encoding.default_external = Encoding::UTF_8
	Encoding.default_internal = Encoding::UTF_8
end

$myDir = File.expand_path(File.dirname(__FILE__))
$LOAD_PATH.unshift($myDir) unless $LOAD_PATH.include?($myDir)

require 'cgi'
require 'rexml/document'
require 'digest/sha2'
require 'securerandom'

require 'jsonRW.rb'
require 'mediaSignageDir.rb'
require 'signage_config.rb'
require "#{$mediaSignage}/platform.rb"

$debug = true
if Platform.type == Platform::WINDOWS
	# Windows packages
	require 'dl/import'
	require 'dl/struct'
	require 'win32ole'
	require 'tempfile'
	require 'win32/service'  
	$htmlDir = "#{$mediaSignage}/status"
else
	$htmlDir = "/Library/WebServer/Documents/signagestatus"
	if not File.directory?($htmlDir)
		$htmlDir = '/opt/local/rails/public/signagestatus'
	end
end
require 'signageLog.rb'

$authKeysPath = "#{$mediaSignage}/status/authKeys.txt"
$passwordSeparator = ';'

# Example of sha256 password
# {sha256};f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2;f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2

def authenticate(response)
	begin
		signageStatusPassword = $config['signageStatusPassword']
		if signageStatusPassword
			authValue = false
			authKey = $cgi['authKey']
			if authKey
				# make sure the file exists
				File.open($authKeysPath, 'a') { |f| }
				# read file
				File.open($authKeysPath, 'r') { |file|
					file.flock(File::LOCK_SH)
					file.each_line { |line|
						a = line.strip.split($passwordSeparator)
						if a.length == 2
							if authKey == a[1]
								if timeToString(Time.now) < a[0]
									authValue = true
								else
									authValue = false
									response['responseStatus'] = "authenticate"
								end
								break
							end
						end
					}
				}
			end
		else
			authValue = true
		end
	rescue Exception => ex
		response['responseStatus'] = "error"
		response['errorMessage'] = "INTERNAL ERROR validating login: #{ex}"
		return false
	end
	if authValue
		return true
	end
	if response['responseStatus'] != "authenticate"
		response['responseStatus'] = "loginError"
		response['errorMessage'] = "Invalid login"
	end
	return false
end

def sendChallenge(response)
	signageStatusPassword = $config['signageStatusPassword']
	if signageStatusPassword.nil?
		signageStatusPassword = ""
	end
	if signageStatusPassword.index('{sha256}') == 0
		arr = signageStatusPassword.split($passwordSeparator)
		if arr.length >= 3
			passwordHash = arr[1]
			salt = arr[2]
			challenge = SecureRandom.hex(32)
		else
			response['responseStatus'] = "error"
			response['errorMessage'] = "Server ERROR reading password}"
			return
		end
	else
		salt = SecureRandom.hex(32)
		challenge = SecureRandom.hex(32)
		passwordHash = Digest::SHA2.hexdigest(signageStatusPassword + salt)
	end
	response['challenge'] = challenge
	response['salt']      = salt
	storeAuthKey(passwordHash, challenge, 2*60*60)
end

def storeAuthKey(passwordHash, challenge, timeout)
	userName = $cgi['userName']
	if userName.nil?
		userName = ""
	end
	authKey = Digest::SHA2.hexdigest(passwordHash + challenge + userName)
	# make sure the file exists
	File.open($authKeysPath, 'a') { |f| }
	# update the file
	File.open($authKeysPath, 'r+') { |file|
		file.flock(File::LOCK_EX)
		# read existing auth keys and remove expired entries
		auth = Array.new
		file.each_line { |line|
			data = line.split($passwordSeparator)
			if data.length == 2
				if timeToString(Time.now) < data[0]
					auth << line
				end
			end
		}
		auth << timeToString(Time.now + timeout) + $passwordSeparator + authKey

		# write the updated auth information
		file.truncate(0)
		file.rewind()
		auth.each { |line|
			file.puts line
		}
	}
end


#----------------------------------------------------------------------------
#
def readStatusFile(response, path)
	return   if response['responseStatus'] != 'success'
	begin
		File.open(path, "r") { |file|
			begin
				statusPlayerControl = JSON.parse(file)
				statusPlayerControl.each { |key, value|
					response['statusInfo'][key] = value
				}
			rescue Exception => ex
				response['responseStatus'] = "error"
				response['errorMessage'] = "ERROR reading '#{path}': #{ex}"
			end
		}
	rescue Exception => ex
		response['responseStatus'] = "error"
		response['errorMessage'] = "ERROR opening '#{path}': #{ex}"
	end
end

#----------------------------------------------------------------------------
#
# Create a time string in RFC 3339 format
def timeToString(time)
	offset = time.utc_offset
	if offset < 0
		sign = '-'
		offset = -offset
	else
		sign = '+'
	end
	offsetHours = (offset / 3600).floor
	offsetMins = ((offset - (offsetHours * 3600)) / 60).floor
	return time.strftime("%Y-%m-%dT%H:%M:%S") + sprintf("%s%02d:%02d", sign, offsetHours, offsetMins)
end


#----------------------------------------------------------------------------
def getSchedule(response)
	begin
		path = "#{$mediaSignage}/content/play.xml"
		File.open(path, "r") { |file|
			response['statusInfo']['scheduleFile'] = file.read(10000000)
		}
		response['statusInfo']['scheduleFileTime'] = timeToString(File.stat(path).mtime)

	rescue Exception => ex
		response['statusInfo']['scheduleFile'] = "ERROR: #{ex}"
		response['statusInfo']['scheduleFileTime'] = ""
		return false
	end
	return true
end

#----------------------------------------------------------------------------
def getManifest(response)
	begin
		path = "#{$mediaSignage}/manifest.xml"
		File.open(path, "r") { |file|
			response['statusInfo']['manifest'] = file.read(10000000)
		}
		response['statusInfo']['manifestTime'] = timeToString(File.stat(path).mtime)

	rescue Exception => ex
		response['statusInfo']['manifest'] = "ERROR: #{ex}"
		response['statusInfo']['manifestTime'] = ""
		return false
	end
	return true
end

#----------------------------------------------------------------------------
def getFileList(response)
	begin
		if Platform.type == Platform::WINDOWS
			cmd = "ls -lR --time-style=\"+%b %d %H:%M:%S %Y\" content receiving_area status manifest.xml config.xml"
			response['statusInfo']['fileList'] = cmd + "\n\n" + Platform.systemTick("cd \"#{$mediaSignage}\" & #{cmd}")
			response['statusInfo']['fileListTime'] = timeToString(Time.now)
		else
			opt = '-lTR'
			if File.exist?('/etc/issue')
				opt = "-lR '--time-style=+%b %d %H:%M:%S %Y'"
			end
			cmd = "ls #{opt} content receiving_area status manifest.xml config.xml"
			response['statusInfo']['fileList'] = cmd + "\n\n" + `cd #{$mediaSignage}; #{cmd}`
			response['statusInfo']['fileListTime'] = timeToString(Time.now)
		end	
	rescue Exception => ex
		response['statusInfo']['fileList'] = "Error"
		response['responseStatus'] = "error"
		response['errorMessage'] = "ERROR getting file list: #{ex}"
		return false
	end
	return true
end

#----------------------------------------------------------------------------
def screenCapture(response)
	begin
		screenCaptureCount = 0
		screenCaptureInterval = 5.0
		if $cgi.has_key?('screencapture')
			screenCaptureCount = $cgi['screencapture'].to_i
		end
		if $cgi.has_key?('screencaptureinterval')
			screenCaptureInterval = $cgi['screencaptureinterval'].to_f
		end

		if screenCaptureCount > 0
			param = Hash.new
			param['screenCaptureCount']    = screenCaptureCount
			param['screenCaptureInterval'] = screenCaptureInterval
			begin
				File.open("#{$mediaSignage}/status/screenCaptureParameters.json", "w") { |file|
					file.chmod(0666)
					JSON.generate(param, file)
				}
			rescue Exception => ex
				response['responseStatus'] = "error"
				response['errorMessage'] = "ERROR writing parameters file: #{ex}"
				return false
			end

			start = Time.now
			while File.exist?("#{$mediaSignage}/status/screenCaptureParameters.json")
				sleep 1.5
				if Time.now > start + 30
					response['responseStatus'] = "error"
					response['errorMessage'] = "ERROR waiting for screen capture"
					return false
				end
			end
			while not File.exist?("#{$mediaSignage}/status/captureCompleteFlag")
				sleep 1.5
				if Time.now > (start + (screenCaptureInterval * screenCaptureCount) + 60)
					response['responseStatus'] = "error"
					response['errorMessage'] = "ERROR completing screen capture"
					return false
				end
			end
		end

	rescue Exception => ex
		response['responseStatus'] = "error"
		msg = "ERROR in screen capture: #{ex}"
		response['errorMessage'] = msg
		$stderr.puts msg
		ex.backtrace.each { |line|
			$stderr.puts "#{line}"
		}
		return false
	end
	return true
end

#----------------------------------------------------------------------------
def getStatusInfo(response)
	status = Hash.new()
	response['statusInfo'] = status

  totalDisk = 0;
  freeDisk = 0;
	# Get free disk space in gigabytes
	if Platform.type == Platform::WINDOWS
		dir = "#{$mediaSignage}/content"
		dirDirCygwin = Platform.fixCygwinPath(dir)
		out = Platform.systemTick("df -Pk \"#{dirDirCygwin}\"")
	else
		out = `df -Pk #{$mediaSignage}/content`
	end
	if out =~ /.*\n[^\s]*\s*(\d+)\s+\d+\s+(\d+)/m
		totalDisk = $1.to_f * 1024.0 / 1000000000.0
		freeDisk = $2.to_f * 1024.0 / 1000000000.0
	end
	status['diskStorageTotal']     = totalDisk
	status['diskStorageAvailable'] = freeDisk

	# $stderr.puts config.inspect
	$config.each { |key, value|
		if not key =~ /password/
			status['config_' + $config.origName(key)] = value
		end
	}

	readStatusFile(response, "#{$mediaSignage}/status/statusPlayerControl.json")
	readStatusFile(response, "#{$mediaSignage}/status/statusFileTransfer.json")
	readStatusFile(response, "#{$mediaSignage}/status/statusPlayer.json")
	readStatusFile(response, "#{$mediaSignage}/status/playedLog.json")

	# gather current screen capture info
	captureArray = Array.new
	num = 1
	while File.exist?("#{$htmlDir}/screenCapture#{num}.png")
		begin
			info = Hash.new
			mtime = File.stat("#{$htmlDir}/screenCapture#{num}.png").mtime
			if Platform.type == Platform::WINDOWS
				info['file'] = "#{$mediaSignageVirtualDirectory}/status/screenCapture#{num}.png"
			else
				info['file'] = "screenCapture#{num}.png"
			end
			info['time'] = timeToString(mtime)
			captureArray << info
		rescue Exception => ex
			response['responseStatus'] = "error"
			response['errorMessage'] = "ERROR getting screen capture info #{ex}"
		end
		num += 1
	end
	status['screenCaptureInfo'] = captureArray

	begin
		File.open("#{$mediaSignage}/version", "r") { |file|
			out = file.read(1000)
			if out =~ /Version ([^ ]+) - /
				status['softwareVersion'] = out.strip()
			else
				status['softwareVersion'] = "Version " + out.strip()
			end
		}
	rescue
	end

	begin
		if Platform.type == Platform::WINDOWS
			data = Platform.systemTick("ver")
			status['osVersion'] = data.strip()
		else
			if File.exist?('/etc/issue')
				File.open('/etc/issue', 'r') { |file|
					data = file.read(10000)
					status['osVersion'] = data.strip()
				}
			else
				if `sw_vers` =~ /ProductName:[ \t]*([^\r\n]*).*?ProductVersion:[ \t]*([^\r\n]*).*?BuildVersion:[ \t]*([^\r\n]*)[\r\n]+/im
					status['osVersion'] = "#{$1} #{$2} (#{$3})"
				end
			end
		end
	rescue
	end

	free        = 0.0
	active      = 0.0
	inactive    = 0.0
	speculative = 0.0
	wired       = 0.0
	begin
# 	sysctl -a | grep -Ei "(hw|vm)\..*mem"
# 	top -l1 -n 20 | grep -Ei "mem|vm"
		if Platform.type == Platform::WINDOWS
		else
			if File.executable?('/usr/bin/vm_stat')
				out = `vm_stat`
				out.split("\n").each { |line|
					if line =~ /Pages free:\s*([^\s]+)/
						free = $1.to_f * 4096.0 / 1048576.0
					end
					if line =~ /Pages active:\s*([^\s]+)/
						active = $1.to_f * 4096.0 / 1048576.0
					end
					if line =~ /Pages inactive:\s*([^\s]+)/
						inactive = $1.to_f * 4096.0 / 1048576.0
					end
					if line =~ /Pages speculative:\s*([^\s]+)/
						speculative = $1.to_f * 4096.0 / 1048576.0
					end
					if line =~ /Pages wired down:\s*([^\s]+)/
						wired = $1.to_f * 4096.0 / 1048576.0
					end
				}
				status['memoryFree']  = free
				status['memoryUsed']  = active + inactive + speculative + wired
				status['memoryTotal'] = free + active + inactive + speculative + wired
	
				if `sw_vers` =~ /ProductName:[ \t]*([^\r\n]*).*?ProductVersion:[ \t]*([^\r\n]*).*?BuildVersion:[ \t]*([^\r\n]*)[\r\n]+/im
					status['osVersion'] = "#{$1} #{$2} (#{$3})"
				end
	
				out = `iostat -c 2 -w 1 disk0`
# 	 			$stderr.puts out.split("\n")[3]
				arr = out.split("\n")[3].split()
				status['diskActivityMBytesPerSec'] = arr[2].to_f
				status['cpuUserPercentage']        = arr[3].to_f
				status['cpuSystemPercentage']      = arr[4].to_f
				status['cpuIdlePercentage']        = arr[5].to_f
				status['cpuLoadAverage1']          = arr[6].to_f
				status['cpuLoadAverage5']          = arr[7].to_f
				status['cpuLoadAverage15']         = arr[8].to_f
			else
				out = `free`
				out.split("\n").each { |line|
					if line =~ /Mem:/
						arr = line.split(' ')
						status['memoryFree']  = arr[3].to_f / 1024.0
						status['memoryUsed']  = arr[2].to_f / 1024.0
						status['memoryTotal'] = arr[1].to_f / 1024.0
					end
				}
	
				out = `iostat -c -d -g allTotal 1 2`
				count = 0
				gotCpu = false
				out.split("\n").each { |line|
					if count == 2 and gotCpu == false
						arr = line.split()
						status['cpuUserPercentage']   = arr[0].to_f
						status['cpuSystemPercentage'] = arr[2].to_f
						status['cpuIdlePercentage']   = arr[5].to_f
						gotCpu = true
					end
					if line =~ /avg-cpu:/
						count += 1
					end
					if count == 2 and line =~ /allTotal/
						arr = line.split(' ')
						status['diskActivityMBytesPerSec']  = (arr[3].to_f + arr[3].to_f) / 1024.0
					end
				}
				out = `uptime`
				if out =~ /\sup\s([^,]*),/
					status['systemUptime'] = $1
				end
				if out =~ /\sload average:\s*([0-9.]+),\s*([0-9.]+),\s*([0-9.]+)/
					status['cpuLoadAverage1']  = $1.to_f
					status['cpuLoadAverage5']  = $2.to_f
					status['cpuLoadAverage15'] = $3.to_f
				end
			end
		end
		getFileList(response)
		getManifest(response)
		getSchedule(response)
	rescue
	end

	begin
		status['errorLog'] = SignageLog.get(30)
	rescue
	end

	status['time'] = timeToString(Time.now)
end


#----------------------------------------------------------------------------
#----------------------------------------------------------------------------
def main()

	$cgi = CGI.new
	puts $cgi.header('application/json')
	response = Hash.new
	response['responseStatus'] = 'success'

	$config = SignageConfig.new
	$config.load("#{$mediaSignage}/config.xml")

	if $cgi.has_key?('authenticate')
		sendChallenge(response)
	else
		if authenticate(response)
# 			if $cgi.has_key?('getschedule') and response['responseStatus'] == 'success'
# 				getSchedule(response)
# 			end
# 			if $cgi.has_key?('getmanifest') and response['responseStatus'] == 'success'
# 				getManifest(response)
# 			end
# 			if $cgi.has_key?('getfilelist') and response['responseStatus'] == 'success'
# 				getFileList(response)
# 			end
			if $cgi.has_key?('screencapture') and response['responseStatus'] == 'success'
				screenCapture(response)
			end
			if $cgi.has_key?('getstatusinfo') and response['responseStatus'] == 'success'
				getStatusInfo(response)
			end
		end
	end

	JSON.generate(response)
end

main()

