#!/usr/bin/ruby
#-------------------------------------------------------------------------------
# = Overview
#    Parameters:
#        name    Base name of the data file
#        data    The data to put into the signage data file
#
# = Copyright
# Created by Ron Alder on 18 Feb 2014.
# Copyright © 2014 Hughes Network Systems an EchoStar company. All rights reserved.
#
#-------------------------------------------------------------------------------

# For ruby 1.9 the encoding must be set or the code may trip over multibyte characters
# in any file that it reads and parses.
if RUBY_VERSION >= "1.9"
	Encoding.default_external = Encoding::UTF_8
	Encoding.default_internal = Encoding::UTF_8
end
# Add the directory of this file to the load search path
mydir = File.expand_path(File.dirname(__FILE__))
$LOAD_PATH.unshift(mydir) unless $LOAD_PATH.include?(mydir)


require 'cgi'
require 'mediaSignageDir'

$debug = false

$dataDir = "#{$mediaSignage}/content/localcontent/data"

#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------

$cgi = CGI.new

# debug junk
if $debug 
	$stderr.puts $cgi.header
	$cgi.params.each { |pName, pValue|
		$stderr.puts "param #{pName} = '#{pValue.first}'"
	}
	$stderr.puts "request_method = '#{$cgi.request_method}'"
	$stderr.puts "accept = '#{$cgi.accept}'"
	$stderr.puts "accept_charset = '#{$cgi.accept_charset}'"
	$stderr.puts "accept_encoding = '#{$cgi.accept_encoding}'"
	$stderr.puts "accept_language = '#{$cgi.accept_language}'"
end

responseFormat = 'application/json'
puts $cgi.header(responseFormat)


responce = "{\"success\": \"Data saved\"}"

begin

	if not File.directory?($dataDir)
		system("mkdir -p -m 777 #{$dataDir}")
	end
	
	data = $cgi['data']
	name = $cgi['name']
	if name and data and (name.length > 0)
		# sanitize name
		name.gsub!(/[\/:]/, '_')
		path = "#{$dataDir}/info_#{name}"
		File.open(path, 'w') { |file|
			file.puts data
			file.chmod(0666)
		}
	else
		responce = "{\"error\": \"Missing parameter\"}"
	end

rescue Exception=>ex
	responce = "{\"error\": \"Internal error: #{ex}\"}"
	$stderr.puts "signage data: Internal error: Could not process request"
	$stderr.puts "#{ex}"
	ex.backtrace.each { |line|
		$stderr.puts line
	}
end

puts responce

