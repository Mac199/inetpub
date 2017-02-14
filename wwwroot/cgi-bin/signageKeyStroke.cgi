#! /usr/bin/ruby
#
# Created by Ron Alder on 11 Feb 2015.
# Copyright © 2015 Hughes Network Systems. All rights reserved.

# For ruby 1.9 the encoding must be set or the code may trip over multibyte characters
# in any file that it reads and parses.
if RUBY_VERSION >= "1.9"
	Encoding.default_external = Encoding::UTF_8
	Encoding.default_internal = Encoding::UTF_8
end

$myDir = File.expand_path(File.dirname(__FILE__))
$LOAD_PATH.unshift($myDir) unless $LOAD_PATH.include?($myDir)

require 'cgi'
require 'mediaSignageDir.rb'

$dataFile = "#{$mediaSignage}/status/keyStrokeData.json"

cgi = CGI.new
puts cgi.header('application/json')

err = nil

if cgi.has_key?('string')
	str = cgi['string']
	if str.length <= 0
		err = "ERROR: string parameter empty"
	end

	unless err
		start = Time.new
		while File.file?($dataFile)
			if Time.new > start + 20
				err = "ERROR: Key stroke data file busy"
				$stderr.puts err
				break
			end
			sleep 0.5
		end
	end

	unless err
		begin
			File.open($dataFile, "w") { |file|
				file.chmod(0666)
				file.puts "{ \"string\": \"#{str}\" }"
			}
			system("sudo #{$mediaSignage}/signalPlayerControl")
		rescue Exception => ex
			err = "ERROR writing key stroke data file: #{ex}"
			$stderr.puts = err
		end
	end
else
	err = "ERROR: string parameter missing"
end

if err
	puts "{ \"status\": \"error\", \"errorMessage\": \"#{err}\" }"
else
	puts "{ \"status\": \"success\" }"
end

