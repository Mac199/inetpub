#!ruby
#
# Created by Ron Alder on 22 May 2013.
# Copyright © 2013 Hughes Network Systems an EchoStar company. All rights reserved.

mydir = File.expand_path(File.dirname(__FILE__))
$LOAD_PATH.unshift(mydir) unless $LOAD_PATH.include?(mydir)

require 'cgi'
#require 'syslog'
require 'jsonRW.rb'
require 'signageLog.rb'

require 'mediaSignageDir'

playerParameters = "#{$mediaSignage}/content/playerParameters.json"
playerTraceLog	 = "#{$mediaSignage}/status/playerTraceLog.txt"
statusFile       = "#{$mediaSignage}/status/statusPlayer.json"
statusFileTmp    = "#{$mediaSignage}/status/statusPlayer.json.tmp"
playedLog        = "#{$mediaSignage}/status/playedLog.json"
playedLogTmp     = "#{$mediaSignage}/status/playedLog.json.tmp"
reportUtility    = "#{$mediaSignage}/play_log.rb"

maxLog = 20

def shEscape(str)
	str.gsub("\\", "\\\\\\").gsub("'", "\\\\'").gsub('"', '\"').gsub('$', '\\$')
end

stat = {}

$cgi = CGI.new
callBack = nil
if $cgi.has_key?('callback')
	callBack = $cgi['callback']
	puts $cgi.header('text/javascript')
else
	puts $cgi.header({'type' => 'application/json',
			'Access-Control-Allow-Origin' => '*',
			'Cache-Control' => 'no-cache',
			'Pragma' => 'no-cache'
			})
end

if $cgi.has_key?('reportPlayed') and $cgi.has_key?('playedFile') and $cgi.has_key?('playedStart') and $cgi.has_key?('playedEnd') and $cgi.has_key?('playedId') and $cgi.has_key?('playedPlaylist') and $cgi.has_key?('programName')
	dateRE = /(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})/
	startTime = "invalid"
	endTime = "invalid"
	
	if dateRE.match($cgi['playedStart'])
		startTime = "#{$1} #{$2}";
	end
	if dateRE.match($cgi['playedEnd'])
		endtime = "#{$1} #{$2}";
	end
	cmd = "ruby \"#{reportUtility}\" --media \"#{shEscape($cgi['playedFile'])}\" --mediaid \"#{$cgi['playedId']}\" -s \"#{startTime}\" -e \"#{endtime}\""
	
	system(cmd)

	# read the updated log file
	played = nil
	begin
		File.open(playedLog, 'r') { |file|
			begin
				played = JSON.parse(file)
			rescue Exception => ex
				played = nil
			end
		}
	rescue
		played = nil
	end
	programName = $cgi['programName']

	if played.nil? or (programName != played['logProgramName'])
		# program has changed so clear played log
		played = Hash.new
		played['logPlayed'] = Hash.new
		played['logProgramName'] = programName
	end

	playlists = played['logPlayed']

	list = playlists[$cgi['playedPlaylist']]
	if list.nil?
		list = Array.new
	end

	entry = {'file'=>$cgi['playedFile'], 'start'=>$cgi['playedStart'], 'end'=>$cgi['playedEnd'], 'id'=>$cgi['playedId'], 'playlist'=>$cgi['playedPlaylist'] }
	list.insert(0, entry)
	
	if list.size > maxLog
		list = list[0, maxLog]
	end
	playlists[$cgi['playedPlaylist']] = list
	
	# write the updated log file
	File.open(playedLogTmp, 'w') { |file|
		JSON.generate(played, file)
	}
	File.rename(playedLogTmp, playedLog)
end

if $cgi.has_key?('errorLog')
#	Syslog.open('SignagePlayer')
#	Syslog.log(Syslog::LOG_ERR, $cgi['errorLog'])
#	Syslog.close()
	if $cgi.has_key?('errorLogTime')
		SignageLog.log($cgi['errorLog'], $cgi['errorLogTime'])
	end
end

if $cgi.has_key?('traceLog')
#	Syslog.open('SignagePlayer')
#	Syslog.log(Syslog::LOG_INFO, $cgi['traceLog'])
#	Syslog.close()
	File.open(playerTraceLog, "a") { |file|
		if $cgi.has_key?('traceLogTime') 
			file.puts($cgi['traceLogTime'] + ": " + $cgi['traceLog'])
		else 
			file.puts($cgi['traceLog'])
		end
	}	
end

$cgi.keys.each { |param|
	stat[param] = $cgi[param]
}

File.open(statusFileTmp, 'w') { |file|
	JSON.generate(stat, file)
}
File.rename(statusFileTmp, statusFile)


File.open(playerParameters) { |file|
	puts "#{callBack}("       if callBack
	puts file.read(10000000)
	puts ");"                 if callBack
}
