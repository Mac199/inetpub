#!/usr/bin/ruby
#-------------------------------------------------------------------------------
# = Overview
# Web API for creating and manipulating MediaSignage local content play list.
# There are four basic operations. create, retrieve, update and destroy. (CRUD)
# URI is /cgi-bin/msLocalcontent.cgi. The HTTP method determines the operation.
# All operations return the modified play list on success or upon failure error
# messages are returned. The returned data is in Json or XML depending$cgi.request_method == "POST"
# on the response format requested in the HTTP header accept field.
#
# = Operations
#
# *  create -
#    Upload new content and create items for each file uploaded.
#    Multiple files may be uploaded with one command. The media type is
#    determined from the file extension. The default duration is set for
#    stills.
#    HTTP method: POST
#    Parameters:
#        file          Name of the file to upload and insert into the playlist
#
# *  retrieve -
#    Returns the current local content play list.
#    HTTP method: GET
#    Returns the play list
#
# *  update -
#    HTTP method: PUT
#    Parameters:
#        id            ID of the play list item to change. (required)
#        type          Media type. [still, video] (optional)
#        duration      Seconds to play content. "0" means play to the end. (optional)
#        moveBeforeId  ID of the place in the play list to move the item.
#                      The item is placed before the moveBeforeId item. (optional)
#        clone         If this parameter is present this item will be duplicate. (optional)
#
# *  destroy -
#    HTTP method: DELETE
#    Parameters:
#        id            ID of the play list item to delete
#
#
# = Copyright
# Created by Ron Alder on 03 May 2012.
# Copyright © 2012 Hughes Network Systems. All rights reserved.
# Changes made by Ron Alder on 26 Aug 2014.
# Copyright © 2014 Hughes Network Systems an EchoStar company. All rights reserved.
#
#-------------------------------------------------------------------------------

# For ruby 1.9 the encoding must be set or the code may trip over multibyte characters
# in any file that it reads and parses.
if RUBY_VERSION >= "1.9"
	Encoding.default_external = Encoding::UTF_8
	Encoding.default_internal = Encoding::UTF_8
end

$mydir = File.expand_path(File.dirname(__FILE__))
$LOAD_PATH.unshift($mydir) unless $LOAD_PATH.include?($mydir)

require 'rexml/document'
require 'fileutils'
require 'digest/md5'
require 'stringio'
require 'cgi'

require 'mediaSignageDir.rb'
require "#{$mediaSignage}/platform.rb"

if Platform.type == Platform::WINDOWS
	# Windows packages
	require 'dl/import'
	require 'dl/struct'
	require 'win32ole'
	require 'tempfile'
	require 'win32/service'  
end

$debug = false

# if File.directory?("/Users/helius")
# 	$mediaSignage = "/Users/helius/MediaSignage"
# else
# 	$mediaSignage = "/Users/support/MediaSignage"
# end
# if not File.directory?($mediaSignage)
# 	$mediaSignage = "/opt/signage/MediaSignage"
# end

$localContentDir = "#{$mediaSignage}/content/localcontent/1"
$descriptionPath = "#{$localContentDir}/description.xml"
$descriptionTmpPath = "#{$localContentDir}/description.xml.tmp"
$configPath = "#{$mediaSignage}/config.xml"

$attributeList = ['type', 'duration', 'start', 'end']
$playlistItems = []
$errors = []
$successMsg = "General success"
$nextId = 1
$descriptionFile = nil
$defaultDuration = '7'



#-------------------------------------------------------------------------------
class MyConfig < Hash

	def initialize
		super
	end

	# Load the hash from an xml file. Save a copy of the old hash for hasChanged?.
	def load(path)
		self.clear
		ret = nil
		begin
			File.open(path, "r") { |file|
				xml = REXML::Document.new(file)
				xml.root.each_element('parameter') { |element|
					attr = element.attributes
					if !(attr['name'].nil? || attr['value'].nil?)
						# lower case all names
						self[attr['name'].downcase.strip] = attr['value'].strip
					end
				}
				if not xml.nil?
					ret = self
				end
			}
		rescue
		end
		return ret
	end
	
	# Make key lookup case insensitive 
	def [](key)
		return self.fetch(key.downcase, nil)
	end
	
	# Down case all keys. Part of making key lookup case insensitive
	def []=(key, value)
		self.store(key.downcase, value)
	end
	
end


#-------------------------------------------------------------------------------
# Convert an object to Json and write it to stdout or a file
#
def writeJson(obj, file=$stdout, indent=0)
	indent += 1
	indentString = "\t"
	comma = ""
	classVal = obj.class
	if obj.class == Hash
		file.print "{"
		obj.each { |key, value|
			file.puts comma
			comma = ","
			file.print "#{indentString * indent}\"#{key}\": "
			writeJson(value, file, indent)
		}
		file.print "\n", indentString * (indent - 1), "}"
	
	elsif obj.class == Array
		file.print "["
		obj.each { |value|
			file.puts comma
			comma = ","
			file.print indentString * indent
			writeJson(value, file, indent)
		}
		file.print "\n", indentString * (indent - 1), "]"
	
	elsif obj.class == Fixnum or obj.class == Bignum or obj.class == Float or obj.class == TrueClass or obj.class == FalseClass
		file.print obj
		
	elsif obj.class == NilClass
		file.print "null"

	elsif obj.kind_of? String
		file.print '"'
		obj.each_byte { |byte|
			case byte
			when 0x22
				file.print '\"'
			when 0x5c
				file.print '\\\\'
			when 0x08
				file.print '\b'
			when 0x0c
				file.print '\f'
			when 0x0a
				file.print '\n'
			when 0x0d
				file.print '\r'
			when 0x09
				file.print '\t'
			else
				file.putc byte
			end
		}
		file.print '"'

	else
		if obj.respond_to? :to_s
			file.print "\"#{obj}\""
		else
			raise "Unsupported object class '#{obj.class}'"
		end
	end
	file.print "\n"   if indent <= 1
end

#-------------------------------------------------------------------------------
# Read playlist description xml file and put the list
# in $playlistItems array.
#
def readDescriptionAndLock()
	doc = nil
	begin
		$playlistItems = []
		$descriptionFile = File.open($descriptionPath, 'r+')
		$descriptionFile.flock(File::LOCK_EX)

		doc = REXML::Document.new($descriptionFile)
		doc.root.elements.each do |element, index|
			attrs = Hash.new
			element.attributes.each { |key, value|
				attrs[key] = value
			}
			if attrs['id']
				id = attrs['id'].to_i
				if id >= $nextId
					$nextId = id + 1
				end
			end
			$playlistItems << attrs
		end
	rescue Exception=>ex
		$stderr.puts "#{ex}"
		ex.backtrace.each { |line|
			$stderr.puts line
		}
		# if the description file is corrupt clean things up
		if $descriptionFile
			$descriptionFile.flock(File::LOCK_UN)
			$descriptionFile.close
		end
		system("rm -f #{$localContentDir}/*")
		FileUtils.mkdir_p($localContentDir, {:mode=>0777})
		$playlistItems = []
		$descriptionFile = File.open($descriptionPath, 'w+')
		$descriptionFile.flock(File::LOCK_EX)
		$descriptionFile.chmod(0666)
		writeDescriptionFile()
	end
end

#-------------------------------------------------------------------------------

def xmlErrors()
	str = ""
	str += "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
	str += "<errors>\n"
	$errors.each { |item|
		str += "    <error "
		item.each { |key, value|
			str += "msg=\"#{value}\" "
		}
		str += "/>\n"
	}
	str += "</errors>\n"
	return str
end

#-------------------------------------------------------------------------------
#
def xmlPlayList()
	str = ""
	str += "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
	str += "<localPlayList>\n"
	$playlistItems.each { |item|
		str += "    <item "
		item.each { |key, value|
			str += "#{key}=\"#{CGI::escapeHTML(value)}\" "
		}
		str += "/>\n"
	}
	str += "</localPlayList>\n"
	return str
end

#-------------------------------------------------------------------------------
#
def signalNewContent()
	signalFile = "#{$mediaSignage}/content/filedownload"
	FileUtils.rm_f(signalFile)
	File.open(signalFile, "w") { |file|
		file.chmod(0666)
	}
end

#-------------------------------------------------------------------------------
# Write new play list discription xml file 
# from $playlistItems array.
#
def writeDescriptionFile()
	if $descriptionFile
		$descriptionFile.truncate(0)
		$descriptionFile.seek(0)
		$descriptionFile.write(xmlPlayList())
	end
end

#-------------------------------------------------------------------------------
# Validate the password parameter
# Return true is password is valid. Otherwise return false.
#
def validatePassword()
	config = MyConfig.new
	config.load($configPath)
	configPassword = config['localContentPassword']
	dur = config['localStillDuration']
	if dur 
		num = dur.to_f
		if num > 0.0
			$defaultDuration = sprintf("%g", num)
		end
	end

	if configPassword.nil? or configPassword == ""
		$errors << {"error"=>"A password has not been setup. See system administrator."}
		return false
	end
	paramPassword = $cgi['password']
	if paramPassword.class == StringIO
		paramPassword = paramPassword.read(10000)
	end
	if paramPassword.nil? or paramPassword == ""
		$errors << {"error"=>"Password is required"}
		return false
	end
	if  Digest::MD5.hexdigest(configPassword) != paramPassword
		$errors << {"error"=>"Invalid password"}
		return false
	end
	return true
end

#-------------------------------------------------------------------------------
#
def processNewFile(fileName, destPath, tmpPath, file)
	if fileName.nil? or fileName == ""
		$textResponse = "Upload error: No file selected"
	end
	if tmpPath && Platform.type != Platform::WINDOWS
		FileUtils.mv(tmpPath, destPath)
	else
		File.open(destPath, "wb") { |f|
			f << file.read
		}
	end
	FileUtils.chmod(0666, destPath)
	
	item = nil
	$playlistItems.each { |x|
		if x['file'] == fileName
			# Override playlist item
			item = x
		end
	}
	if item.nil?
		# Add new item to playlist
		item = Hash.new
		item['id'] = $nextId.to_s
		$nextId += 1
		$playlistItems << item
	end
	item['file'] = fileName
	$attributeList.each { |key|
		if $cgi.has_key?(key)
			value = $cgi[key]
			if value.class == StringIO
				value = value.read(10000)
			end
			item[key] = value.nil? ? '' : value
		end
	}
	if not item['type']
		if fileName =~ /.*\.([^.]*)$/
			extension = $1
		end
		case extension.downcase
		when 'bmp', 'dib', 'did', 'exif', 'gif', 'jfif', 'j2c', 'j2k', 'jp2', 'jpeg', 'jpf', 'jpg', 'jpx', 'pbm', 'pcd', 'pct', 'pcx', 'pdf', 'pic', 'pict', 'png', 'qti', 'qtif', 'rgb', 'sgi', 'svg', 'targa', 'tga', 'tif', 'tiff', 'wmf', 'yuv'
			item['type'] = 'still'
		else
			item['type'] = 'video'
		end
	end
	if not item['duration']
		if item['type'].downcase == 'still'
			item['duration'] = $defaultDuration
		else
			item['duration'] = '0'
		end
	end
end

def myBaseName(path)
	return path.gsub(%r!.*[\\/:]!, '')
end

#-------------------------------------------------------------------------------
# - create -
# upload and add file to local content list
# PUT http method
#
def create()
	if $cgi.params.has_key? "file"
		$cgi.params["file"].each { |file|
			fileName = myBaseName(file.original_filename.untaint)
			destPath = "#{$localContentDir}/#{fileName}"
			tmpPath = file.local_path
			
			processNewFile(fileName, destPath, tmpPath, file)
		}
	
	elsif $cgi.params.has_key? "file[filename]"
		$cgi.params["file[filename]"].each_index { |index|
			fileName = myBaseName($cgi.params["file[filename]"][index])
			destPath = "#{$localContentDir}/#{fileName}"
			tmpPath = $cgi.params["file[path]"][index]
			
			processNewFile(fileName, destPath, tmpPath, nil)
		}
	else
		$errors << {"error"=>"Internal error: Invalid file parameter"}
		return
	end
	writeDescriptionFile()
	$successMsg = "File uploaded"
	signalNewContent()
end


#-------------------------------------------------------------------------------
# - retrieve -
# Return play list
# GET http method
#
def retrieve()
	$successMsg = "list"
end

#-------------------------------------------------------------------------------
# - update -
# Edit play list attributes
# and reorder list
# PUT http method
#
def update()
	editId = $cgi['id']
	editIndex = nil
	moveBeforeId = $cgi['moveBeforeId']
	moveBeforeIndex = nil
	$playlistItems.each_index { |index|
		id = $playlistItems[index]['id']
		if editId == id
			editIndex = index
		end
		if moveBeforeId == id
			moveBeforeIndex = index
		end
	}
	if editIndex
		item = $playlistItems[editIndex]
		$attributeList.each { |key|
			item[key] = $cgi[key]     if $cgi.has_key?(key)
		}
		if moveBeforeId and moveBeforeId != ""
			if moveBeforeId == "-1"
				moveBeforeIndex = -1
			end
			if moveBeforeIndex
				item = $playlistItems[editIndex]
				$playlistItems.insert(moveBeforeIndex, item.dup)
				$playlistItems.delete_if { |x| x.equal?(item) }
				editIndex = moveBeforeIndex
			else
				$errors << {"error"=>"Internal error: Move before item '#{moveBeforeId}' not found"}
			end
		end
		if $cgi.has_key?('clone') and $cgi['clone'].downcase == 'true'
			dupItem = item.dup
			dupItem['id'] = $nextId.to_s
			$nextId += 1
			$playlistItems.insert(editIndex, dupItem)
		end
		writeDescriptionFile()
		signalNewContent()
	else
		$errors << {"error"=>"Internal error: Edit item '#{editId}' not found"}
	end
end

#-------------------------------------------------------------------------------
# - destroy -
# Delete and item from the play list
# DELETE http method
# 
#
def destroy()
	deleteId = $cgi['id']
	deleteItem = nil
	fileName = nil
	$playlistItems.each { |item|
		if deleteId == item['id']
			deleteItem = item
			fileName = item['file']
		end
	}
	# look for duplicate entries for this file
	multiEntryFlag = false
	$playlistItems.each { |item|
		if deleteId != item['id'] and fileName and fileName == item['file']
			multiEntryFlag = true
		end
	}
	if deleteItem
		$playlistItems.delete(deleteItem)
		writeDescriptionFile()
		if fileName and not multiEntryFlag
			File.delete("#{$localContentDir}/#{fileName}")
		end
		$successMsg = "Item deleted"
		signalNewContent()
	else
		$errors << {"error"=>"Delete item not found"}
	end
end


#-------------------------------------------------------------------------------
# Start a background process that will transfer content from the directory specified
# by the uri parameter.
#
def startFileSync()
	if $cgi.has_key?('uri')
		uri = $cgi['uri']
		File.open("#{$localContentDir}/.syncParameter", 'w') { |file|
			file.puts uri
			file.chmod(0666)
		}
		File.open("#{$localContentDir}/.syncStart", 'w') { |file|
			file.puts "A checkered flag"
			file.chmod(0666)
		}
		$textResponse = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
		$textResponse += "<success>\n"
		$textResponse += "    Started file download\n"
		$textResponse += "</success>\n"
	else
		$errors << {"error"=>"Missing parameter uri"}
	end
end

#-------------------------------------------------------------------------------
def sendResponse()
	if $textResponse
		puts $textResponse
	
	elsif $cgi.accept.index('application/json')
		if $errors.length <= 0
			writeJson({"success"=>$successMsg, "playlist"=>$playlistItems})
		else
			writeJson({"errors"=>$errors})
		end
		
	else
		if $errors.length <= 0
			$stdout.print xmlPlayList()
		else
			$stdout.print xmlErrors()
		end
	end
end


#-------------------------------------------------------------------------------
#-------------------------------------------------------------------------------
#    main code 

# Hack warning
# ruby 2.0 has put a limit on uploading files at 128M bytes
# The limit is set by a constant in cgi/core.rb.
# Since constants and variables are basically the same thing in ruby
# a work around is to change the constant to 128Gig.
begin
	CGI::MAX_MULTIPART_LENGTH = 128 * 1024 * 1024 * 1024
rescue
end

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

responseFormat = 'application/xml'
if $cgi.request_method == "POST"
	responseFormat = 'text/plain; charset=utf-8'
elsif $cgi.accept.index('application/json')
	responseFormat = 'application/json'
end
puts $cgi.header(responseFormat)


begin
	readDescriptionAndLock()

	if not validatePassword()
		# invalid password
		if $cgi.request_method == "POST"
			$textResponse = $errors[0]['error']   if $errors[0]
		end

	elsif $cgi.request_method == "POST"
		$textResponse = "Internal error: Could not process POST request."
		create()
		if $errors.length <= 0
			$textResponse = "Upload successful"
		else
			$textResponse = "Upload error"
		end

	elsif $cgi.request_method == "PUT" or ($cgi.has_key?('command') and ($cgi['command'] == 'update'))
		update()

	elsif $cgi.request_method == "DELETE" or ($cgi.has_key?('command') and ($cgi['command'] == 'destroy'))
		destroy()

	elsif $cgi.request_method == "GET" and ($cgi.has_key?('command') and ($cgi['command'] == 'sync'))
		startFileSync()

	elsif $cgi.request_method == "GET"
		retrieve()

	else
		$errors << {"error"=>"Internal error: Invalid request method"}
	end
rescue Exception=>ex
	$errors << {"error"=>"Internal error: Could not process request."}
	$stderr.puts "msLocalContent Internal error: Could not process request"
	$stderr.puts "#{ex}"
	ex.backtrace.each { |line|
		$stderr.puts line
	}
end

sendResponse()
if $descriptionFile
	$descriptionFile.flock(File::LOCK_UN)
	$descriptionFile.close
end
