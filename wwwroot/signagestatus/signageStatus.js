// Created by Ron Alder on 22 Feb 2013.
// Copyright © 2013 Hughes Network Systems. All rights reserved.
//------------------------------------------------------------------------------




//------------------------------------------------------------------------------
function PageController()
{
	var mySelf = this;

	this.captureInterval = 5.0;

	this.userName = "anonymous";
	this.password = "";
	this.authKey = "";
	this.expandFlag = false;

	if (window.sessionStorage) {
		this.authKey = window.sessionStorage['signageStatusAuthKey'];
		if (this.authKey === undefined) {
			this.authKey = "";
		}
	}

	$("#loginBlock").hide();
	$("#theBody").hide();
	$("#logout").hide();

	// LOGOUT by clearing the password
	$("#logout").bind("click", function() {
		if (window.sessionStorage) {
			window.sessionStorage.setItem('signageStatusAuthKey', "");
			mySelf.authKey = "";
		}
		location.reload();
	});

	$("#login").bind("click", function() {
		mySelf.login();
	});
	$("#password").focus();

	$("#password").bind("keypress", function(e) {
	   if (e.keyCode == 13) {
			mySelf.login();
		   return false; // ignore default event
	   }
	});

	$("#expand").bind("click", function() {
		mySelf.expand();
	});

	this.capturingScreen = true;
	this.getInfo();
}

PageController.prototype.expand = function()
{
	var panels = [
		"#collapseOne",
		"#collapseTwo",
		"#collapseThree",
		"#collapseFour",
		"#collapseFive",
		"#collapseSix",
		"#collapsePlayed0",
		"#collapsePlayed1",
		"#collapsePlayed2",
		"#collapsePlayed3",
		"#collapsePlayed4",
		"#collapsePlayed5",
		"#collapsePlayed6",
		"#collapsePlayed7",
		"#collapsePlayed8",
		"#collapsePlayed9"];

	var navTabs = [
		"#manifestTab",
		"#scheduled-contentTab",
		"#directory-listingTab",
		"#parametersTab"];

	var tabPanes = [
		"#manifest",
		"#scheduled-content",
		"#directory-listing",
		"#parameters"];

	var i;
	var l;

	if (this.expandFlag) {
		for (i = 0, l = panels.length; i < l; ++i) {
			$(panels[i]).removeClass('in');
			$(panels[i]).addClass('collapse');
		}
		for (i = 0, l = navTabs.length; i < l; ++i) {
			$(navTabs[i]).removeClass('active');
		}
		for (i = 0, l = tabPanes.length; i < l; ++i) {
			$(tabPanes[i]).removeClass('active');
		}
		$("#expand").html("<span class='glyphicon glyphicon-plus-sign'></span> Expand All");
		this.expandFlag = false;

	} else {
		for (i = 0, l = panels.length; i < l; ++i) {
			$(panels[i]).addClass('in');
			$(panels[i]).removeClass('collapse');
			$(panels[i]).css('height', 'auto');
		}
		for (i = 0, l = navTabs.length; i < l; ++i) {
			$(navTabs[i]).removeClass('active');
		}
		for (i = 0, l = tabPanes.length; i < l; ++i) {
			$(tabPanes[i]).addClass('active');
		}
		$("#expand").html("<span class='glyphicon glyphicon-minus-sign'></span> Collapse All");
		this.expandFlag = true;
	}
};

PageController.prototype.getInfo = function()
{
	this.clearError();

	$.ajax({
		url: "../cgi-bin/getSignageStatus.cgi",
		type: "post",
		data: { getstatusinfo: "",
		        authKey: this.authKey
		      },
		dataType: "json", // data type of response
		context: this,
		success: function(response) {
			if (this.responseErrorCheck(response, "reading status info", this.getInfo, this)) {
				return;
			}
			this.insertAllInfo(response.statusInfo);
		},
		error: function(jqXHR, textStatus, errorThrown) {
			console.log("error  Status");
			this.error("Error reading Status");
		}
	});
};


PageController.prototype.insertAllInfo = function(statusInfo)
{
	var mySelf = this;

	this.info = statusInfo;

	if (this.capturingScreen) {
		this.startScreenCapture();
	}

	$("#theBody").show();
	if (this.authKey == "") {
		$("#logout").hide();
	} else {
		$("#logout").show();
	}
	var timePlayer = this.info['timePlayer'];
	if (timePlayer) {
		this.timeCurrent = new Date(timePlayer);
	} else {
		this.timeCurrent = new Date();
	}

	$("*[info]").each(function(index, element) {
		mySelf.infoProcess(this);
	});

	this.capturingScreen = false;
};

PageController.prototype.infoProcess = function(element)
{
	if (this.info['sling_layout']) {
		$("#slingStatus").show();
	} else {
		$("#slingStatus").hide();
	}
	var jElement = $(element);
	var type = jElement.attr('type');
	var name = jElement.attr('info');
	var value = this.info[name];

	if (type == 'playerType') {
		this.infoPlayerType(jElement, name, value);

	} else if (type == 'time') {
		this.infoTime(jElement, name, value);

	} else if (type == 'screenCapture') {
		this.screenCapture(jElement, name, value);

	} else if (type == 'transferBar') {
		this.transferBar(jElement, name, value);

	} else if (type == 'number') {
		this.number(jElement, name, value);

	} else if (type == 'rawStatus') {
		this.rawStatus(jElement, name, value);

	} else if (type == 'contentPlayed') {
		this.contentPlayed(jElement, name, value);

	} else if (type == 'errorHistory') {
		this.errorHistory(jElement, name, value);

	} else if (type == 'lastLogMessage') {
		this.lastLogMessage(jElement, name, value);

	} else if (type == 'playerStatus') {
		this.playerStatus(jElement, name, value);

	} else if (type == 'downloadStatus') {
		this.downloadStatus(jElement, name, value);

	} else {
		this.infoString(jElement, name, value);
	}
};

PageController.prototype.downloadStatus = function(element, name, value)
{
	if (!this.info) {
		return;
	}
	if (this.info.transferPercent >= 100.0) {
		$("#downloadBar").hide();
		$("#downloadStatus").hide();
		$("#downloadComplete").show();
	} else {
		$("#downloadBar").show();
		$("#downloadStatus").show();
		$("#downloadComplete").hide();
	}
};

PageController.prototype.playerStatus = function(element, name, value)
{
	if (!this.info) {
		return;
	}
	var str = value;
	if (this.info.display && this.info.display == 'off') {
		str += ", display off";
	}
	element.text(str);
};

PageController.prototype.lastLogMessage = function(element, name, value)
{
	if (!this.info) {
		return;
	}
	var history = this.info.errorLog;
	if (!history || !history[0]) {
		return;
	}
	element.text(this.formatLogEntry(history[0]));
};

PageController.prototype.errorHistory = function(element, name, value)
{
	if (!this.info) {
		return;
	}
	var history = this.info.errorLog;
	if (!history) {
		return;
	}
	var html = "";
	for (var i = 0; i < history.length; i++) {
		html += "<tr><td>";
		html += this.escapeHtml(this.formatLogEntry(history[i]));
		html += "</td></tr>\n";
	}
	element.html(html);
};

PageController.prototype.formatLogEntry = function(logEntry)
{
	var ret = "";
	var arr = logEntry.split(" ");
	var ts = new Date(arr[0]);
	if (ts && ! isNaN(ts.valueOf())) {
		ret += this.formatDate(ts);
	}
	for (var x = 1; x < arr.length; x++) {
		ret += " ";
		ret += arr[x];
	}
	return ret;
};

PageController.prototype.contentPlayed = function(element, name, value)
{
	if (!this.info) {
		return;
	}

	var playlists = this.info.logPlayed;
	if (!playlists) {
		return;
	}
	var names = new Array;
	for (var key in playlists) {
		names.push(key);
	}
	names.sort();

	var coll;
	if (this.expandFlag) {
		coll = "in";
	} else {
		coll = "collapse";
	}

	var html = "";
	html += "<div class='panel-group' id='accordionPlayed'>\n";

	for (var i = 0; i < names.length; i++) {
		html += "    <div class='panel panel-default'>\n";
		html += "        <div class='panel-heading2'>\n";
		html += "            <h4 class='panel-title'>\n";
		html += "                <a data-toggle='collapse' data-parent='#accordionPlayed' href='#collapsePlayed" + i + "'>\n";
		html += "                    " + this.escapeHtml(names[i]) + " playlist\n";
		html += "                </a>\n";
		html += "            </h4>\n";
		html += "        </div>\n";
		html += "        <div id='collapsePlayed" + i + "' class='panel-collapse " + coll + "'>\n";
		html += "            <div class='panel-body'>\n";
		html += "                <table class='table table-striped table-condensed'>\n";

		html += "<tr>\n";
		html += "  <td>\n";
		html += "    <div class='subject-color playedFile'>File </div>\n";
		html += "    <div class='subject-color playedTime'>Time </div>\n";
		html += "  </td>\n";
		html += "</tr>\n";
		var currentFile = this.info['currentlyPlaying-' + names[i]];
		if (currentFile) {
			html += "<tr>\n";
			html += "  <td>\n";
			html += "    <div class='playedFile'>" + this.escapeHtml(currentFile) + "</div>\n";
			html += "    <div class='playedTime'>currently playing</div>\n";
			html += "  </td>\n";
			html += "</tr>\n";
		}
		var list = playlists[names[i]];
		for (var x = 0; x < list.length; x++) {
			var file = list[x].file;
			var start = new Date(list[x].start);

			if (file && ! isNaN(start.valueOf())) {
				html += "<tr>\n";
				html += "  <td>\n";
				html += "    <div class='playedFile'>" + this.escapeHtml(file) + "</div>\n";
				html += "    <div class='playedTime'>" + this.escapeHtml(this.formatDate(start)) + "</div>\n";
				html += "  </td>\n";
				html += "</tr>\n";
			}
		}

		html += "                </table>\n";
		html += "            </div>\n";
		html += "        </div>\n";
		html += "    </div>\n";
	}

	html += "</div>\n";

	element.html(html);
};

PageController.prototype.rawStatus = function(element, name, value)
{
	if (!this.info) {
		return;
	}
	var keys = new Array;
	for (var key in this.info) {
		keys.push(key);
	}
	keys.sort();
	var str = "";
	for (var i = 0; i < keys.length; i++) {
		var key2 = keys[i];
		if (key2 != 'manifest' && key2 != 'scheduleFile' && key2 != 'fileList' && key2 != 'errorLog') {
			str += keys[i] + ": " + this.info[keys[i]] + "\n";
		}
	}
	element.text(str);
};

PageController.prototype.number = function(element, name, value)
{
	if (value === undefined) {
    	element.text("");
    	return;
	}
	var num = value;
	var fixed = element.attr('fixed');
	if (fixed) {
		element.text(num.toFixed(parseFloat(fixed)));
		return;
	}

	var multiplier = element.attr('multiplier');
	if (multiplier) {
		num *= multiplier;
	}
    var i = 0;
    var units = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y'];
	while (num > 1024 && i < 8) {
        num = num / 1024;
        i++;
	}
    element.text(num.toFixed(i == 0 ? 0 : 1) + ' ' + units[i]);
};

PageController.prototype.transferBar = function(element, name, value)
{
	element.css('width', value + '%');
	element.attr('aria-valuenow', value);
};

PageController.prototype.zeroPad = function(num, size)
{
    var s = num + "";
    while (s.length < size) s = "0" + s;
    return s;
};

PageController.prototype.screenCapture = function(element, name, value)
{
	var screenCapture = this.info['screenCaptureInfo'];
	var m = name.match(/screenCapture([^0-9]+)(\d+)/);
	if (!m) {
		return;
	}
	var index = 0;
	if (m[2]) {
		index = parseInt(m[2]);
		if (index > 0) {
			index -= 1;
		}
	}

	var screen;
	if (screenCapture) {
		screen = screenCapture[index];
	}
	if (m[1] == 'Time') {
		if (this.capturingScreen) {
			element.text("...");
		} else {
			if (screen && screen['time']) {
				this.infoTime(element, name, screen['time']);
			} else {
				element.html("ERROR");
				element.addClass('error');
			}
		}
	} else if (m[1] == 'Image') {
		if (this.capturingScreen) {
			element.attr('src', 'loadingScreenCapture.jpg');
		} else {
			if (screen && screen['file']) {
				var now = new Date();
				element.attr('src', screen['file'] + "?_t=" + now.getTime());
			} else {
				element.attr('src', 'errorScreenCapture.jpg');
			}
		}
	}
};

PageController.prototype.formatDate = function(date)
{
	var dayOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
	var monthName = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

	var ampm = "am";
	var hours = date.getHours();
	if (hours >= 12) {
		ampm = "pm";
	}
	if (hours > 12) {
		hours -= 12;
	}
	if (hours == 0) {
		hours = 12;
	}
	if (hours == 12) {
		ampm = "pm";
	}

	return dayOfWeek[date.getDay()] + " " +
		monthName[date.getMonth()] + " " +
		date.getDate().toFixed(0) + " " +
		date.getFullYear().toFixed(0) + " " +
		hours + ":" +
		this.zeroPad(date.getMinutes(), 2) + ":" +
		this.zeroPad(date.getSeconds(), 2) + " " +
		ampm;
};

PageController.prototype.infoTime = function(element, name, value)
{
	var timeObj = new Date(value);
	if (isNaN(timeObj.valueOf())) {
		element.html("");
		return;
	}

	element.text(this.formatDate(timeObj));

	var limit = 0.0;
	var more = false;
	var less = false;
	var limitString = element.attr('errorIfMoreThan');
	if (limitString !== undefined) {
		more = true;
	} else {
		limitString = element.attr('errorIfLessThan');
		if (limitString !== undefined) {
			less = true;
		}
	}
	if (limitString !== undefined) {
		var match = limitString.match(/([\d.]+)(?::(\d+))?/);
		if (match && match[1]) {
			limit = parseInt(match[1], 10);
		}
		if (match && match[2]) {
			limit *= 60;
			limit += parseInt(match[2], 10);
		}
	}
	if (more && ((this.timeCurrent - timeObj) > (limit * 60 * 1000))
	    || less && ((this.timeCurrent - timeObj) < (limit * 60 * 1000)))
	{
		element.addClass('error');
	} else {
		element.removeClass('error');
	}
};

PageController.prototype.infoString = function(element, name, value)
{
	element.text(value);
};

PageController.prototype.infoPlayerType = function(element, name, value)
{
	var type;
	if (value == 0) {
		type = "Mac";

	} else if (value == 2) {
		type = "Linux";

	} else if (value == 3) {
		type = "Windows";

	} else {
		type = "unknown";
	}

	element.text(type);
};

PageController.prototype.error = function(message)
{
	$("#errorMessage").text(message);
	$("#errorMessage").addClass('error');
	$("#errorMessage").show();
	console.log(message);
};

PageController.prototype.clearError = function()
{
	$("#errorMessage").hide();
	$("#errorMessage").html("");
	$("#errorMessage").removeClass('error');
};

PageController.prototype.startScreenCapture = function()
{
	this.clearError();
	$.ajax({
		url: "../cgi-bin/getSignageStatus.cgi",
		type: "post",
		data: { screencapture: "3",
		        screencaptureinterval: this.captureInterval.toFixed(1),
		        authKey: this.authKey
		      },
		dataType: "json", // data type of response
		context: this,
		success: function(response) {
			if (this.responseErrorCheck(response, "screen capture", this.refresh, this)) {
				return;
			}
			this.getInfo();
		},
		error: function(jqXHR, textStatus, errorThrown) {
			this.error("Error refreshing status");
		}
	});
};

PageController.prototype.login = function()
{
	this.password = $('#password').val();
	window.sessionStorage.setItem('signageStatusHash', "");
	$('#password').val("");
	$("#loginBlock").hide();
	this.clearError();
	this.authenticate(this.getInfo, this);
};

PageController.prototype.authenticate = function(callBack, context)
{
	if (this.password == "") {
		// show login
		$("#theBody").hide();
		$("#logout").hide();
		$("#loginBlock").show();
		$("#password").focus();
		return;
	}

	$.ajax({
		url: "../cgi-bin/getSignageStatus.cgi",
		type: "post",
		data: { authenticate: "",
		        userName: this.userName
		      },
		dataType: "json", // data type of response
		context: this,
		success: function(response) {
			if (this.responseErrorCheck(response, "reading schedule", callBack, context)) {
				return;
			}
			if (response['challenge'] && response['salt']) {
				this.authKeyGeneration(response['challenge'], response['salt']);
				var now = new Date();
				if (this.authCallBackLast && ((now - this.authCallBackLast) < 5000)) {
					setTimeout($.proxy(callBack, context), 3 * 1000);
				} else {
					callBack.call(context);
				}
				this.authCallBackLast = now;
			}
		},
		error: function(jqXHR, textStatus, errorThrown) {
			this.error("Error authenticating");
		}
	});
};

PageController.prototype.authKeyGeneration = function(challenge, salt)
{
	this.authKey = hex_sha256(hex_sha256(this.password + salt) + challenge + this.userName);
	if (window.sessionStorage) {
		window.sessionStorage.setItem('signageStatusAuthKey', this.authKey);
	}
	return this.authKey;
};

PageController.prototype.escapeHtml = function(string)
{
	var entityMap = {
		"&": "&amp;",
		"<": "&lt;",
		">": "&gt;",
		'"': '&quot;',
		"'": '&#39;',
		"/": '&#x2F;'
	};
	return String(string).replace(/[&<>"'\/]/g, function (s) {
		return entityMap[s];
	});
};

PageController.prototype.durationString = function(date1, date2)
{
	var delta = date1 - date2;
	if (isNaN(delta)) {
		return "";
	}
	if (delta < 0) {
		delta = -delta;
	}

	var days = Math.floor(delta / (24 * 60 * 60 * 1000));
	delta -= days * 24 * 60 * 60 * 1000;
	var hours = Math.floor(delta / (60 * 60 * 1000));
	delta -= hours * 60 * 60 * 1000;
	var mins = Math.floor(delta / (60 * 1000));
	delta -= mins * 60 * 1000;
	var secs = Math.floor(delta / (1000));

	var str;
	if (days > 0) {
		str = days + " days ";
	} else {
		str = "";
	}
	str += this.numPad(hours) + ":" + this.numPad(mins) + ":" + this.numPad(secs);

	return str;
};

PageController.prototype.numPad = function(num)
{
	return num < 10 ? '0' + num : num;
};

PageController.prototype.responseErrorCheck = function(response, message, retryFunction)
{
	if (! response) {
		this.error("ERROR " + message + " no response");
		return true;
	}
	if (! response.responseStatus) {
		this.error("ERROR " + message + " no status");
		return true;
	}
	if (response.responseStatus == 'authenticate') {
		if (window.sessionStorage) {
			window.sessionStorage.setItem('signageStatusAuthKey', "");
			this.authKey = "";
		}
		this.authenticate(retryFunction);
		return true;
	}
	if (response.responseStatus != 'success') {
		if (response.responseStatus == 'loginError') {
			if (window.sessionStorage) {
				window.sessionStorage.setItem('signageStatusAuthKey', "");
				this.authKey = "";
			}
			$("#loginBlock").show();
			$("#password").focus();
			$("#theBody").hide();
			$("#logout").hide();
			if (this.password == "") {
				return true;
			}
		}
		if (response.errorMessage) {
			this.error(response.errorMessage);
		} else {
			this.error("Known error from server");
		}
		return true;
	}
	return false;
};


//------------------------------------------------------------------------------
$(document).ready(function() {
	new PageController();
});

