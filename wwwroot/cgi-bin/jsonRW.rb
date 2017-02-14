#! /usr/bin/ruby
#
# =Copyright
# Created by Ron Alder on 28 Aug 2012.
# Copyright © 2012 Hughes Network Systems. All rights reserved.
#
# = Description
#-------------------------------------------------------------------------------

require "stringio"

module JSON

	def self.generate(obj, file=$stdout)
		if file.nil?
			io = StringIO.new()
			self.toJson(obj, io)
			return io.string
		else
			self.toJson(obj, file)
			return nil
		end
	end

	class ParseJson

		def startParse(inp)
			if inp.class == String
				@input = StringIO.new(inp)
			else
				@input = inp
			end
			@string = ""
			@index = 0
			@line = 1
			@ch = ' '
			if value()
				return @value
			else
				raise "JSON syntax error: line #{@line}: first value invalid'"
			end
		end

		def nextChar()
			if @ch == nil
				raise "JSON error: line #{@line}: unexpected EOF or file read error"
			end
			@ch = @string[@index, 1]
			if @ch == ""
				@ch = nil
			end
			if @ch.nil?
				begin
					@string = @input.readline
					@index = 0
					@ch = @string[@index, 1]
					if @ch == ""
						@ch = nil
					end
				rescue
					@ch = nil
				end
			end
			@index += 1
			return @ch
		end

		def unNextChar()
			@index -= 1
			@ch = @string[index, 1]
			# test for new line, and carriage return
			if @ch == "\n" or @ch == "\r"
				@line -= 1
			end
		end

		def skipWhite()
			lineBump = 0
			while true
				# test for space, tab, backspace and form feed
				unless @ch == " " or @ch == "\t" or @ch == "\b" or @ch == "\f" or @ch == "\r"
					# test for new line, and carriage return
					if @ch == "\n"
						lineBump += 1
					else
						@line += lineBump
						return @ch
					end
				end
				nextChar()
			end
		end

		def value()
			if (s = string())
				@value = s
				return true
			elsif (n = number())
				@value = n
				return true
			elsif (o = object())
				@value = o
				return true
			elsif (o = array())
				@value = o
				return true
			elsif @string[@index-1, 5] == "false"
				@value = false
				@index += 4
				nextChar()
				return true
			elsif @string[@index-1, 4] == "true"
				@value = true
				@index += 3
				nextChar()
				return true
			elsif @string[@index-1, 4] == "null"
				@value = nil
				@index += 3
				nextChar()
				return true
			end
			return nil
		end

		def number()
			if @string[@index-1, @string.length - @index + 1] =~ (/^([-+]*[0-9]*[.]*[0-9]*[eE]*[-+]*[0-9]+)/)
				@index += $1.length - 1
				nextChar()
				return $1.to_f
			end
			return nil
		end

		def string()
			skipWhite()
			str = ""
			if @ch != '"'
				return nil
			end
			nextChar()
			while @ch
				if @ch == '"'
					nextChar()
					return str

				elsif @ch == "\\"       # back slash
					nextChar()
					case @ch
					when "\\", '/'
						str << @ch
					when 'b'
						str += "\b"
					when 'f'
						str += "\f"
					when 'n'
						str += "\n"
					when 'r'
						str += "\r"
					when 't'
						str += "\t"
					when 'u'
						digits = @string[@index, 4]
						if digits =~ /([0-9a-fA-F]{4})/
							str << $1.to_i(16)
							@index += 3
							nextChar()
						else
							raise "JASON invalid string: line #{@line}: invalid \\uXXXX"
						end
					else
						str << @ch
					end
				else
					str << @ch
				end
				nextChar()
			end
			return nil
		end

		def pair(obj)
			if (s = string())
				skipWhite()
				if @ch != ':'
					raise "JSON syntax error: line #{@line}: expecting ':'"
				end
				nextChar()
				if value()
					obj[s] = @value
					return true
				else
					raise "JSON syntax error: line #{@line}: expecting value"
				end
			end
			return false
		end

		def object()
			skipWhite()
			if @ch == '{'
				nextChar()
				obj = Hash.new()
				pair(obj)
				skipWhite()
				while @ch == ','
					nextChar()
					unless pair(obj)
						next
					end
				end
				skipWhite()
				if @ch == '}'
					nextChar()
					return obj
				else
					raise "JSON syntax error: line #{@line}: missing '}'"
				end
			end
			return nil
		end

		def array()
			skipWhite()
			if @ch == '['
				nextChar()
				arr = Array.new()
				if value()
					arr << @value
				end
				skipWhite()
				while @ch == ','
					nextChar()
					if value()
						arr << @value
					else
						next
					end
				end
				skipWhite()
				if @ch == ']'
					nextChar()
					return arr
				else
					raise "JSON syntax error: line #{@line}: missing ']'"
				end
			end
			return nil
		end

	end

	def self.parse(str)
		parser = ParseJson.new()
		return parser.startParse(str)
	end

	def self.toJson(obj, file=$stdout, indent=0)
		indent += 1
		indentString = "\t"
		comma = ""
		if obj.kind_of? Hash
			file.print "{"
			keys = obj.keys
			keys.sort!
			keys.each { |key|
				value = obj[key]
				file.puts comma
				comma = ","
				file.print "#{indentString * indent}\"#{key}\": "
				self.toJson(value, file, indent)
			}
			file.print "\n", indentString * (indent - 1), "}"

		elsif obj.kind_of? Array
			file.print "["
			obj.each { |value|
				file.puts comma
				comma = ","
				file.print indentString * indent
				self.toJson(value, file, indent)
			}
			file.print "\n", indentString * (indent - 1), "]"

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
					if byte <= 0x1f
						file.printf("\\u%04x", byte)
					else
						file.putc byte
					end
				end
			}
			file.print '"'
		
		elsif obj.kind_of? Numeric
			if obj.kind_of?(Float) && (! obj.finite?)
				raise "JSON Unsupported Float value, NaN or Infinite"
			end
			file.print obj
		
		elsif obj.instance_of? TrueClass
			file.print "true"

		elsif obj.instance_of? FalseClass
			file.print "false"

		elsif obj.instance_of? NilClass
			file.print "null"

		else
			if obj.respond_to? :to_s
				file.print "\"#{obj}\""
			else
				raise "JSON Unsupported object class '#{obj.class}'"
			end
		end
		file.print "\n"   if indent <= 1
	end

end


#-------------------------------------------------------------------------------
# ------------ Test Code ------------
# Normally this file is included by other files making this code not used.
# If this file is executed from the command line this code will display
# diagnostic information useful for development.
if __FILE__ == $0
	if ARGV[0] != nil
		obj = JSON.parse(File.open(ARGV[0]))
	else
		# More complex test case does not work on Windows
		obj = JSON.parse('  { "fish" : 25.3e2, "The truth":true, "Not the truth" : false, "nothing" :null, "array" : [1,"two",{"three":3}, ], "string" : "q\"\\\/\b\f\n\r\t\u0091 end"  }')
		obj['backslash'] = '\n\l\1'
	end

	puts obj.class
	puts obj.inspect

	JSON.generate(obj)
end




