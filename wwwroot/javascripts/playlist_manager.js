$(document).ready(function() {

	// needed to detect ipad or computer for click or touches
	var ua = navigator.userAgent, event = (ua.match(/iPad/i)) ? "touchstart" : "click";

	// The root URL for the RESTful services
	var rootURL = "/cgi-bin/msLocalContent.cgi";

	// hide progress class when the user is using IE
	$('.progress').hide();
	$("#spinner").hide();

	$("#epg_password").focus();

	$('#startDate').datepicker({
		autoclose: true,
		clearBtn: true,
		todayHighlight: false
	});
	$('#endDate').datepicker({
		autoclose: true,
		clearBtn: true,
		todayHighlight: false
	});
	$("#startDate").change(function () {
		var start = new Date($("#startDate").val());
		var end = new Date($("#endDate").val());
		if (!isNaN(start.valueOf()) && !isNaN(end.valueOf()) && (start.getTime() > end.getTime())) {
			alert("Start date must be before end date.");
			$(this).val("");
		}
		$('#endDate').datepicker('setStartDate', $("#startDate").val());
	});
	$("#endDate").change(function () {
		var start = new Date($("#startDate").val());
		var end = new Date($("#endDate").val());
		if (!isNaN(start.valueOf()) && !isNaN(end.valueOf()) && (start.getTime() > end.getTime())) {
			alert("End date must be after start date.");
			$(this).val("");
		}
		$('#startDate').datepicker('setEndDate', $("#endDate").val());
	});

	// CREATE
	/* 	http://stackoverflow.com/questions/5392344/sending-multipart-formdata-with-jquery-ajax */
		var first_time = true;
		var bar;
		var percent;
		// make sure to md5 the password
		var status;
		$('form').ajaxForm({
/* 			data: { password:crypted_password }, */
/* 			dataType: "json", // data type of response */
			beforeSend: function() {
				status = $('#status');
				$('#status').show();
				$('.progress').show();
				$("#spinner").show();
				status.empty();
				$(".progress").html("");
				first_time = true;
				// This line causes problems for IE 9.
				// $('#file_field').attr("disabled", true);
				$('#subBtn').attr("disabled", true);
				return true;
			},
			uploadProgress: function(event, position, total, percentComplete) {
				$("#spinner").hide();
				$('.progress').show();
				if (first_time) {
					first_time = false;
					$(".progress").html("<div class='bar'></div><div class='percent'></div>");
					bar = $('.bar');
					percent = $('.percent');
					var percentVal = '0%';
					bar.width(percentVal)
					percent.html(percentVal);
				}
				var percentVal = percentComplete + '%';
				bar.width(percentVal)
				percent.html(percentVal);

			},
			complete: function(xhr) {
				$("#spinner").hide();
				status.html(xhr.responseText);
				findAll();
				$('.progress').delay(3000).fadeOut(1000);
				$('#status').delay(3000).fadeOut(1000);
				// This line causes problems for IE 9.
				// $('#file_field').attr("disabled", false);
				$('#subBtn').attr("disabled", false);

			}
		});

	// LOGOUT by clearing the password
	$("#logout").bind("click", function() {
		location.reload();
	});

	$("#authForm").bind("keypress", function(e) {
	   if (e.keyCode == 13) {
			$('#passwordfield').remove();
			$('#msLocalContent').append("<input id='passwordfield' name='password' value=" + getCryptedPass() + " type='hidden' />");
			findAll();
		   return false; // ignore default event
	   }
	});

	$("#msLocalContent").bind("keypress", function(e) {
	   if (e.keyCode == 13) {
			var start = new Date($("#startDate").val());
			if ($("#startDate").val() != "" && isNaN(start.valueOf())) {
				alert("Start date is invalid.");
				$("#startDate").val("");
				$('#endDate').datepicker('setStartDate', "");
			}
			var end = new Date($("#endDate").val());
			if ($("#endDate").val() != "" && isNaN(end.valueOf())) {
				alert("End date is invalid.");
				$("#endDate").val("");
				$('#startDate').datepicker('setEndDate', "");
			}
		   return false; // ignore default event
	   }
	});

	// READ on click
	$("#loadPlaylist").bind("click", function() {
		$('#passwordfield').remove();
		$('#msLocalContent').append("<input id='passwordfield' name='password' value=" + getCryptedPass() + " type='hidden' />");
		findAll();
	});

	function getCryptedPass() {
		var pass = $('#epg_password').val();
		var crypted_password = hex_md5(pass);
		return crypted_password;
	}

	// READ on page load
	function findAll() {
		var pass = $('#epg_password').val();
		var crypted_password = hex_md5(pass);
		$('.alert').remove();
		var d = Date();
		$.ajax({
			type: 'GET',
			url: "http://" + window.location.host + rootURL+'?password='+crypted_password + '&dummy='+d,
			dataType: "json", // data type of response
			success: function(response) {
				renderList(response);
				errorList(response);
			}

		});
	}

	function renderList(data) {
		// JAX-RS serializes an empty list as null, and a 'collection of one' as an object (not an 'array of one')
		var list = data == null ? [] : (data.playlist instanceof Array ? data.playlist : [data.playlist]);

		$('.playlistItem').remove();
		if (data.playlist instanceof Array) {
			$.each(list, function(index,playlist) {
				// build up an html string for the playlist item
				
				var duration = playlist.duration;
				var type = playlist.type;
				var start = playlist.start;
				var end = playlist.end;
				
				if (duration == "0" && type == "video") {
					duration = "na"
				}
				if (start == "") {
					start = "<span class='grayed'>now</span>"
				}
				if (end == "") {
					end = "<span class='grayed'>never</span>"
				}
				
				html = ""
				html += "<tr id='"+playlist.id+"' class='playlistItem'>"
				html += "<td>"+playlist.file+"</td>"
				html += "<td class='dur'>"+duration+"</td>"
				html += "<td class='typ'>"+type+"</td>"
				html += "<td class='start'>"+start+"</td>"
				html += "<td class='end'>"+end+"</td>"
				html += "<td class='act'>"
				html += "<a style='margin-left:10px;'id='"+playlist.id+"' class='btn btn-danger' href='#'>"
				html += "<i class='icon-trash icon-white'></i> Delete</a>"
				html += "<a style='margin-left:10px; "
				html += "padding-right:15px; padding-left:15px;' id='"+playlist.id+"' class='btn btn-primary edit' "
				html += "href='#'><i class='icon-edit icon-white'></i> Edit</a></td>"
				html += "</tr>"
				$('#playList').append(html);
				
			});
		}
	}

/*
# *  update -
#    HTTP method: PUT
#    Parameters:
#        id            ID of the play list item to change. (required)
#        type          Media type. [still, video] (optional)
#        duration      Seconds to play content. "0" means play to the end. (optional)
#        moveBeforeId  ID of the place in the play list to move the item.
#                      The item is placed before the moveBeforeId item. (optional)
*/

	// UPDATE (reorder playlist item)
	// uses JQuery UI for basic sorting
	// uses Touch Punch for sorting on IPAD
	$("#playList tbody.playlistContent").sortable({
		stop: function(event, ui) {

			$('.progress').hide();
			dropped_id_str = ui.item[0].attributes.getNamedItem('id').nodeValue;

			// loop over the whole table and get the move_before_id
			$("tr").each(function(index) {
				row_id = $(this).attr('id');
				if (dropped_id_str == row_id) {
					move_before_id = $(this).next().attr('id');
					if (move_before_id == undefined) {
						move_before_id = "-1"
					}
				}
			});

			// make a request to the server to update the list, kickoff findAll
			$.ajax({
				type: "PUT",
				url: "http://" + window.location.host + rootURL,
				data: "id=" + dropped_id_str + "&moveBeforeId=" + move_before_id + "&password=" + getCryptedPass(),
				success: function(data, textStatus, jqXHR){
						findAll();
				},
				error: function(jqXHR, textStatus, errorThrown){
					alert('communication error');
				}
	
			});

/* 			alert("dropped id:" +dropped_id_str+ " New position: " + ui.item.index() + " Before ID: " + move_before_id); */
			
		},  // end of stop callback
		cursor: 'move',
		helper: function(e, tr)
		{
			var $originals = tr.children();
			var $helper = tr.clone();
			$helper.children().each(function(index)
			{
				// Set helper cell sizes to match the original sizes
				$(this).width($originals.eq(index).width())
			});
			return $helper;
		}  // end of helper callback


	}); // end of sortable


	// PRE-UPDATE (Turns 1 playlist row into an editable row)
	$(document).on("click", ".edit", function(){
		item_id = this.id;
		var dataString = 'id=' + item_id + '&password=' + getCryptedPass()
		
		$('.edit').hide();
		$('.btn-danger').hide();

		// loop over the whole table and change the table to input fields
		$("tr").each(function(index) {
			row_id = $(this).attr('id');
			if (item_id == row_id) {
				var dur = $(this).children('.dur').text();
				var typ = $(this).children('.typ').text();
				var start = $(this).children('.start').text();
				if (isNaN(new Date(start))) {
					start = "";
				}
				var end = $(this).children('.end').text();
				if (isNaN(new Date(end))) {
					end = "";
				}
				
				// setup the duration for editing, only on stills
				if (typ=="still") {
					$(this).children('.dur').html("<input id='dur_field' type='text' value='"+dur+"'></input>");
				}
				
				// setup the type for editing
				if (typ=="still")
				{
					part1 = "<option value='still' selected='selected'>still</option>";
					part2 = "<option value='video'>video</option>";
				}
				else
				{
					part1 = "<option value='still'>still</option>";
					part2 = "<option value='video' selected='selected'>video</option>";
				}
				$(this).children('.typ').html("<select id='type_field'>"+part1+part2+"</select>");
				$(this).children('.start').html("<input id='start_field' type='text' value='"+start+"' placeholder='now'></input>");
				$(this).children('.end').html("<input id='end_field' type='text' value='"+end+"' placeholder='never'></input>");
				
				// put a 'done editing' in place of default actions
				prt1 = "<div class='form-inline'><label class='checkbox'><input type='checkbox' id='dup_field'/> Duplicate</label>"
				prt2 = "<a style='margin-left:15px; margin-right:15px; padding-right:15px; padding-left:15px;' id='"+item_id+"' class='btn btn-primary done-edit' href='#'><i class='icon-edit icon-white'></i> Save</a></div>";
				$(this).children('.act').html(prt1+prt2);
				// turn off sorting while editing a row
				$( "#playList tbody.playlistContent" ).sortable( "option", "disabled", true );

				$('#start_field').datepicker({
					autoclose: true,
					clearBtn: true,
					todayHighlight: false
				});
				$('#end_field').datepicker({
					autoclose: true,
					clearBtn: true,
					todayHighlight: false
				});
				$("#start_field").change(function () {
					var start = new Date($("#start_field").val());
					var end = new Date($("#end_field").val());
					if (!isNaN(start.valueOf()) && !isNaN(end.valueOf()) && (start.getTime() > end.getTime())) {
						alert("Start date must be before end date");
						$(this).val("");
					}
					$('#end_field').datepicker('setStartDate', $("#start_field").val());
				});
				$("#end_field").change(function () {
					var start = new Date($("#start_field").val());
					var end = new Date($("#end_field").val());
					if (!isNaN(start.valueOf()) && !isNaN(end.valueOf()) && (start.getTime() > end.getTime())) {
						alert("End date must be after start date");
						$(this).val("");
					}
					$('#start_field').datepicker('setEndDate', $("#end_field").val());
				});
				$("#start_field").bind("keypress", function(e) {
				   if (e.keyCode == 13) {
						var start = new Date($("#start_field").val());
						if ($("#start_field").val() != "" && isNaN(start.valueOf())) {
							alert("Start date is invalid");
							$("#start_field").val("");
							$('#end_field').datepicker('setStartDate', "");
						}
					   return false; // ignore default event
				   }
				});
				$("#end_field").bind("keypress", function(e) {
				   if (e.keyCode == 13) {
						var end = new Date($("#end_field").val());
						if ($("#end_field").val() != "" && isNaN(end.valueOf())) {
							alert("End date is invalid");
							$("#end_field").val("");
							$('#start_field').datepicker('setEndDate', "");
						}
					   return false; // ignore default event
				   }
				});
			}
		});

	});

	// confirm and warn user when changing the media type
	var previous;
	$(document).on("change", "#type_field", function(){
		change_to = $('select option:selected').val();
		if (change_to == "video"){
			previous = "still";
		}
		else if (change_to == "still"){
			previous = "video";
		}
		var change_confirm = confirm("Modifying media type could make this content unplayable.  Change media type to '" + change_to + "'");
		// .blur() is used to remove the focus so that the previous is always a valid value
		$("#type_field").blur();
		// if change_confirm is false change it back to previous
		if (change_confirm == false) {
			$('#type_field :selected').removeAttr("selected");
			$('#type_field').val(previous);
		}
/* 		alert('\n\r change: ' + change_confirm + '\n\r previous: ' + previous + '\n\r change_to: ' + change_to    ); */
	});
		

	// UPDATE (Saves an edited table row)
	$(document).on("click", ".done-edit", function(){
		item_id = this.id;
		var dur;
		var typ;
		var dup;
		var start;
		var end;
		
		// loop over the whole table and change the table to input fields
		$("tr").each(function(index) {
			row_id = $(this).attr('id');
			if (item_id == row_id) {
				dur = $('#dur_field').val();
				typ = $('#type_field').val();
				start = $('#start_field').val();
				end = $('#end_field').val();
				dup = $('#dup_field').is(":checked");
			}
		});

/* 		If type changes from still to video set duration to 0 seconds but display NA */
		if (typ == "video") {
			dur = "0";
		}

/* 		If type changes from video to still set duration to 7 seconds */
/* 		Stills cannot be set to duration of 0 seconds */
		if (typ == "still" && dur == "0") {
			dur = "7";
		}
		else if (typ =="still" && dur == undefined) {
			dur = "7";
		}
		
		// make ajax call and update durs and types
		$.ajax({
			type: "PUT",
			url: "http://" + window.location.host + rootURL,
			data: "id=" + item_id + "&duration=" + dur + "&type=" + typ + "&start=" + start + "&end=" + end + "&password=" + getCryptedPass() + "&clone=" + dup,
			success: function(data, textStatus, jqXHR){
					findAll();
			},
			error: function(jqXHR, textStatus, errorThrown){
				alert('communication error');
			}

		});
		
		// turn sorting back on
		$( "#playList tbody.playlistContent" ).sortable( "option", "disabled", false );

	});

	// DELETE (deletes one playlist item)
	$(document).on("click", ".btn-danger", function(){
		item_id = this.id;
		var dataString = 'id=' + item_id + '&password=' + getCryptedPass() + '&dummy='+d

		// make a request to the server to delete a specific playlist item
		var d = Date();
		$.ajax({
			url: "http://" + window.location.host + rootURL,
			type: "DELETE",
			dataType: "json", // data type of response
			data: dataString,
			success: function(data, textStatus, jqXHR){
					findAll();
					errorList(data);
			},
			error: function(jqXHR, textStatus, errorThrown){
				alert('communication error in delete');
			}

		});

	});
	
	// renders any errors that come back from an ajax JSON request
	function errorList(data) {
		var list = data == null ? [] : (data.errors instanceof Array ? data.errors : [data.errors]);
		if (data.errors instanceof Array) {
			$('#alert').remove();
			$('#authForm').show();
			$.each(list, function(index, errors) {
				$('.span4').append("<div id='alert' class='alert alert-block alert-error fade-in'>"+errors.error+"</div>");
			});
		}
		else {
			$('#authForm').hide();
			$('#playlistManager').show();
			$('#playList').show();
			$('#logout').show();
		}
	}

});    // end of JQUERY READY
