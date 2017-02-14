#
# =Copyright
# Created by Ron Alder on 2/18/2010.
# Copyright (c) 2010 Helius LLC
# Copyright © 2012 Hughes Network Systems
# Copyright © 2013 Hughes Network Systems
#
# All rights reserved.  Unauthorized reproduction of this software is
# prohibited and is in violation of United States copyright laws.
#
# = Description
# A container for MediaSignage configuration information.
#
# Once the config information is loaded it can be access like a hash object.
#
# The special feature of this hash include
# * case insensitive keys
# * load method used to read the contents from an xml file
# * hasChanged? method that indicates if the value of a key has changed from the
#   previous load.
#
class SignageConfig < Hash

	def initialize
		super
		@oldConfig = nil
		@origName = nil
		@daysOfWeek = {
			'sun'=>0, 'sunday'=>0,
			'mon'=>1, 'monday'=>1,
			'tue'=>2, 'tuesday'=>2,'tu'=>2, 'tues'=>2,
			'wed'=>3, 'wednesday'=>3,
			'thu'=>4, 'thursday'=>4, 'thur'=>4, 'thurs'=>4, 'th'=>4, 'thu'=>4,
			'fri'=>5, 'friday'=>5,
			'sat'=>6, 'saturday'=>6
		}
	end

	# Load the hash from an xml file. Save a copy of the old hash for hasChanged?.
	def load(path)
		@origName = Hash.new
		@oldConfig = nil
		@oldConfig = self.dup
		self.clear
		ret = nil
		begin
			File.open(path, "r") { |file|
				xml = REXML::Document.new(file)
				xml.root.each_element('parameter') { |element|
					attr = element.attributes
					if !(attr['name'].nil? || attr['value'].nil?)
						@origName[attr['name'].downcase.strip] = attr['name'].strip
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

	# Get the name with its original case
	def origName(name)
		return @origName[name.downcase]
	end

	# Make key lookup case insensitive
	def [](key)
		return self.fetch(key.downcase, nil)
	end

	# Down case all keys. Part of making key lookup case insensitive
	def []=(key, value)
		self.store(key.downcase.strip, value.strip)
	end

	# Convert config value to a floating point number.
	# If key is not found return default.
	def float(key, default=0.0)
		str = self.fetch(key.downcase, nil)
		if not str.nil?
			return str.to_f
		end
		return default
	end

	# Convert config value to an integer number.
	# If key is not found return default.
	def integer(key, default=0)
		str = self.fetch(key.downcase, nil)
		if not str.nil?
			return str.to_i
		end
		return default
	end

	# Convert config interval to a floating point number.
	# An interval is of the form HH:MM:SS. Hours and Minutes are optional.
	# 2:10 -> 130
	# 1:01:20 -> 3680
	# 135 -> 135
	# If key is not found return default.
	def interval(key, default=0.0)
		str = self.fetch(key.downcase, nil)
		if not str.nil?
			ret = 0.0;
			str.split(/:/).each { |str2|
				ret += (ret * 60.0) + str2.to_f
			}
			return ret
		end
		return default
	end

	# Get value of key and see if time is in the range.
	# Example of range is 01300400 for time range 1:30am to 4:00am.
	# Return true is time is in the range or key not set or invalid
	# Return false if key is valid range and time not in range
	def timeRangeCheck(key, time)
		value = self.fetch(key.downcase, nil)
		if value and value =~ /(\d\d)(\d\d)(\d\d)(\d\d)/
			startHour = $1.to_i
			startMin = $2.to_i
			endHour = $3.to_i
			endMin = $4.to_i
			hour = time.hour
			min = time.min
			if startHour < endHour or (startHour == endHour and startMin < endMin)
				return ((hour > startHour or (hour == startHour and min >= startMin)) and
				       (hour < endHour or (hour == endHour and min < endMin)))
			else
				return ((hour > startHour or (hour == startHour and min >= startMin)) or
				       (hour < endHour or (hour == endHour and min < endMin)))
			end
		end
		return true
	end

	# Interpret config value as a boolean
	# Return true if the config value indicates true.
	# Return false if the config value indicates false.
	# Return the default value if value is not set or does not match the list.
	def boolean(key, default=false)
		value = self.fetch(key.downcase, nil)
		if value
			if value.strip =~ /^(true|t|yes|y|on|1|enable|enabled|positive|pro|allow|active|activate|accept|trust)$/i
				return true
			end
			if value.strip =~ /^(false|f|no|n|off|0|disable|disabled|negative|con|deny|inactive|deactivate|reject|distrust|mistrust)$/i
				return false
			end
		end
		return default
	end

	# Returns true if the value for this key changed during the last load.
	def hasChanged?(key)
		return self[key] != @oldConfig[key]
	end

	# Returns the previous config object
	def old()
		return @oldConfig
	end

	# Parses event time and returns the time of the next event
	# or nil if event time is not specified or invalid.
	# An event time specifies the time that an event should occur each day.
	# If day names are specified then the event only occurs on those days.
	# Times format is HH:MM with HH being 00-23 and MM being 00-59.
	# Day names are Sun, Mon, Tue, Wed, Thu, Fri and Sat. Day name case is
	# not importent. If the keyword monthly is included then the event will
	# occur once a month on the first day of the month at the specified time.
	# If a day of the week is included with monthly then
	# the event will be on the first day of the month matching that day of the week.
	def nextEventTime(key)
		value = self.fetch(key.downcase, nil)
		return nil    if value.nil?
		vals = value.split(/[\s,\.]+/)
		now = Time.now()
		currentTime  = now.hour * 60 + now.min
		currentDow   = now.wday
		currentMonth = now.month
		currentYear  = now.year
		currentDay   = now.day
		monthlyFlag  = false
		times = Array.new
		dows = Array.new
		vals.each { |v|
			if v =~ /(^\d{1,2})[:;](\d\d)$/
				h = $1.to_i
				m = $2.to_i
				times << h * 60 + m    if h >= 0 and h < 24 and m >= 0 and m < 60
				next
			end
			dow = @daysOfWeek[v.downcase]
			if not dow.nil?
				dows << dow

				elsif v.downcase =~ /month/
				monthlyFlag = true
			end
		}
		return nil    if times.length == 0

		nextEvent = nil
		times.sort!()
		dows.sort!()
		nextTime = nil
		times.each { |t|
			if monthlyFlag
				n = addDayOfWeekSpecification(Time.local(currentYear, currentMonth, 1) + (t * 60), dows)
				if n and n < now
					month = currentMonth + 1
					if month > 12
						month = 1
						year = currentYear + 1
					else
						year = currentYear
					end
					n = addDayOfWeekSpecification(Time.local(year, month, 1) + (t * 60), dows)
				end
			else
				n = addDayOfWeekSpecification(Time.local(currentYear, currentMonth, currentDay) + (t * 60), dows)
				if n < now
					n = addDayOfWeekSpecification(Time.local(currentYear, currentMonth, currentDay) + (t * 60) + 24*60*60, dows)
				end
			end

			if n
				if n >= now and (nextEvent.nil? or n < nextEvent)
					nextEvent = n
				end
			end
		}

		return nextEvent
	end


private
	# Add the day of the week specification to the given time.
	# Used by nextEventTime.
	def addDayOfWeekSpecification(time, dows)
		currentDow = time.wday
		nextDow = nil
		dows.each { |d|
			if d < currentDow
				dd = d + 7
			else
				dd = d
			end
			if nextDow.nil? or (dd < nextDow)
				nextDow = dd
			end
		}
		if nextDow
			return time + (nextDow - currentDow) * 24 * 60 * 60
		end
		return time
	end
end

