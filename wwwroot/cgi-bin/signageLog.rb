#! /usr/bin/ruby
#
# = Copyright
# Created by Ron Alder on 03 Feb 2014.
# Copyright © 2014 Hughes Network Systems an EchoStar company. All rights reserved.
#
# = Description
#-------------------------------------------------------------------------------

# For ruby 1.9 the encoding must be set or the code may trip over multi-byte characters
# in any file that it reads and parses.
if RUBY_VERSION >= "1.9"
	Encoding.default_external = Encoding::UTF_8
	Encoding.default_internal = Encoding::UTF_8
end

$myDir = File.expand_path(File.dirname(__FILE__))
if $myDir.downcase().include? "cgi"
	require 'mediaSignageDir.rb'
else	
	$mediaSignage   = File.expand_path("~/MediaSignage")
end

module SignageLog

	@name_error = "errorLog"
	@name_debug = "debugLog"
	@ext = "txt"
	@maxFileSize = 1000000
	@numOldFiles = 10

	def self.log(message, timeString)
		begin
			filePath = "#{$mediaSignage}/status/#{@name_error}.#{@ext}"
			if File.exist?(filePath)
				nowTime = Time.now
				fileTime = File.mtime(filePath)
				if(nowTime.day != fileTime.day)
					self.age(@name_error)
				end
			end
			fileSize = File.size?(filePath)
			File.open(filePath, 'a') { |file|
				file.flock(File::LOCK_EX)
				file.chmod(0666)     if fileSize.nil?
				file.puts "#{timeString} #{message}"
			}
			log_debug(message, timeString)
		rescue
			# ignored
		end
	end

	def self.log_debug(message, timeString)
		begin
			filePath = "#{$mediaSignage}/status/#{@name_debug}.#{@ext}"
			if File.exist?(filePath)
				nowTime = Time.now
				fileTime = File.mtime(filePath)
				if(nowTime.day != fileTime.day)
					self.age(@name_debug)
				end
			end
			fileSize = File.size?(filePath)
			File.open(filePath, 'a') { |file|
				file.flock(File::LOCK_EX)
				file.chmod(0666)     if fileSize.nil?
				file.puts "#{timeString} #{message}"
			}
		rescue
			# ignored
		end
	end
	
	def self.age(name)
		begin
			basePath = "#{$mediaSignage}/status/#{name}"
			if not File.exist?("#{basePath}.#{@ext}")
				return
			end
			File.open("#{basePath}.#{@ext}.lck", 'w') { |file|
				file.flock(File::LOCK_EX)
				i = @numOldFiles - 1
				if File.exist?("#{basePath}.#{i}.#{@ext}")
					File.delete("#{basePath}.#{i}.#{@ext}")
				end
				i -= 1
				while i >= 0
					if File.exist?("#{basePath}.#{i}.#{@ext}")
						File.rename("#{basePath}.#{i}.#{@ext}", "#{basePath}.#{i+1}.#{@ext}")
					end
					i -= 1
				end
				File.rename("#{basePath}.#{@ext}", "#{basePath}.0.#{@ext}")
			}
			File.delete("#{basePath}.#{@ext}.lck")
		rescue
			# ignored
		end
	end

	def self.get(numOfLines)
		begin
			ret = Array.new
			File.open("#{$mediaSignage}/status/#{@name_error}.#{@ext}", 'r') { |file|
				file.flock(File::LOCK_EX)
				file.readlines.each { |line|
					ret.unshift(line)
					if ret.size > numOfLines
						ret.pop
					end
				}
				if ret.size < numOfLines
					more = Array.new
					moreCount = numOfLines - ret.size
					if File.exist?("#{$mediaSignage}/status/#{@name_error}.0.#{@ext}")
						File.open("#{$mediaSignage}/status/#{@name_error}.0.#{@ext}", 'r') { |file0|
							file0.readlines.each { |line|
								more.unshift(line)
								if more.size > moreCount
									more.pop
								end
							}
						}
						ret = more + ret
					end
				end
			}
			ret.each { |line|
				line.strip!
			}
			return ret
		rescue
			return Array.new
		end
	end
end

