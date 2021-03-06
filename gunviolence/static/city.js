var selected_dt;
var res = {};
var comm_data = {};
var polypaths = [];
var map = null;
var heatmap = null;
var prev_poly = null;
var prev_infowindow_poly = null;
var prev_infowindow_marker = null;
var map_polygons = [];
var map_heatmarks = [];
var map_markers = [];
var mark_labels = [];
var city = $("meta[name='city']").attr("content"); 
var date_dropdown = $("meta[name='date_dropdown']").attr("content").replace(/\[|\]|'/g, "").split(", ")
var community_name = city;
var community_id;
var censusChart;
var census_opt;
var crimetype_opt;
var field;
var z;
var last_point;
var scatterX;
var scatterY;
var timedPlay;


chartCrimeSeries();
$.getJSON($SCRIPT_ROOT + '/community_pivot/' + city + '/0', function(json) {
		res = json;
	});


$.getJSON($SCRIPT_ROOT + '/census/' + city , function(json) {
		comm_data = json;
	});

$('.btn-primary').on('change', function(){
    dropDownSelect();
}); 

google.maps.event.addDomListener(window, 'load', initMap);

$(document).ready(function() {
	$("#btn-back").click(function(event){
		nextButton(-1);
	});
	$("#btn-fwd").click(function(event){
		nextButton(1);
	});
	$("#btn-play").click(function(event){
		timedPlay = playButton();
	});
	$("#btn-pause").click(function(event){
		clearInterval(timedPlay);
	});
	$("ul.dropdown-menu").click(function(event){
		clearInterval(timedPlay);
	});
});


function playButton() {
	var timedPlay = setInterval(function(){
		nextButton(1);
	}, 1000);
	return timedPlay
}

function nextButton(i) {
	if (res.results[selected_dt]) {
		var slider_idx = Number($("#date-slider").val());
		if (slider_idx+i == date_dropdown.length) {
			slider_idx = 0; 
		} else if (slider_idx+i == -1){
			slider_idx = date_dropdown.length-1;
		} else {
			slider_idx += i;
		}
		$("#date-slider").val(slider_idx.toString());
		sliderOption();
	}
}

function initMap() {
	$("#myDropdown").hide();
	$("#xDropdown").hide();
	$("#yDropdown").hide();	
	$("#censusDropdownValue").hide();
	$("#censusDropdownX").hide();
	$("#censusDropdownY").hide();
	$("#transformX").hide();
	$("#transformY").hide();
	$('.play').hide()
	
	z = res.map_dict.maptype_control;
    document.getElementById('view-side').style.display = 'block';
    map = new google.maps.Map(
	    document.getElementById('view-side'), {
	        center: new google.maps.LatLng(res.map_dict.center[0], res.map_dict.center[1]),
	        zoom: res.map_dict.zoom,
	        zoomControlOptions: {
		        position: google.maps.ControlPosition.LEFT_CENTER
		    },
	        mapTypeId: google.maps.MapTypeId.ROADMAP,
	        zoomControl: res.map_dict.zoom_control,
	        mapTypeControl: z,
	        scaleControl: true,
	        streetViewControl: res.map_dict.streetview_control,
	        rotateControl: res.map_dict.rorate_control,
	        scrollwheel: res.map_dict.scroll_wheel,
	        fullscreenControl: res.map_dict.fullscreen_control
    });
    map.addListener('click', function(event) {
		if (prev_infowindow_poly) {
			prev_infowindow_poly.close();
		}
	})
	map.addListener('zoom_changed', sliderOption);
}


function getMonthName(selected_dt) {
	var yr = selected_dt.split("-")[0];
	var m = selected_dt.split("-")[1] - 1;
	var dt_obj = new Date(yr, m);
	var monthName = dt_obj.toString().split(" ")[1];
	return [monthName, yr]
}

function dateLabel() {
	var dt = document.getElementById("date-label");
	var dt_list = getMonthName(selected_dt);
	dt.innerHTML = community_name.toUpperCase().replace("_", " ") + " - " + dt_list[0].toUpperCase() + ". " + dt_list[1];
}






function sliderOption() {
	var slider_idx = $("#date-slider").val();
	selected_dt = date_dropdown[slider_idx];
	dateLabel();	

	if (!$('.form-check-input:checked').val()){
		$('.form-check-input[value="community"]').prop("checked", true)
	}
	if ($('.form-check-input[value="community"]').is(':checked')) {
		if (community_name.toUpperCase().replace("_", " ")==city.toUpperCase().replace("_", " ")) {
			$("#chart1").hide();
			$("#chart4").hide();
			$("#myDropdown").hide();
			$("#xDropdown").hide();
			$("#yDropdown").hide();
			$("#censusDropdownValue").hide();
			$("#censusDropdownX").hide();
			$("#censusDropdownY").hide();
			$("#transformX").hide();
			$("#transformY").hide();
		}
		$("#chart2").hide();
		$("#chart3").hide();
		$('.play').hide();
		$.getJSON($SCRIPT_ROOT + '/community_pivot/' + city + '/' + selected_dt, function(json) {
			res = json;
			removeMarkers();
			if (map_polygons.length > 0) {
		    	updatePoly(res);
		    }
		    else {
				drawPoly(res);
		    }
	        if (map_heatmarks.length > 0) {
		    	removeHeatmap();
		    }
			if (prev_infowindow_poly) {
				comm_idx = Object.values(res.results.COMMUNITY).indexOf(community_name);
				var content = "<p>" + res.results.COMMUNITY[comm_idx] + "</p><p>Gun crimes: " + res.results[selected_dt][comm_idx] + "</p>";
				prev_infowindow_poly.setContent(content);
			}
		});
		moveWithSlider(slider_idx);
	}
	if ($('.form-check-input[value="heatmap"]').is(':checked')) {
		$("#myDropdown").hide();
		$("#xDropdown").hide();
		$("#yDropdown").hide();
		$("#censusDropdownValue").hide();
		$("#censusDropdownX").hide();
		$("#censusDropdownY").hide();
		$("#transformX").hide();
		$("#transformY").hide();
		$("#chart1").hide();
		$("#chart2").hide();
		$("#chart3").hide();
		$("#chart4").hide();
		$('.play').show();
		community_name = city;
		dateLabel();
		addCitySeries();
		census_opt = null;
		$.getJSON($SCRIPT_ROOT + '/heatmap/' + city + '/' + selected_dt, function(json) {
			res = json;
			removeMarkers();
			if (map_heatmarks.length > 0) {
				updateHeatmap(res);
			}
			else {
				drawHeatmap(res);
			}
			if (map_polygons.length > 0) {
				removePoly();
			}
			
		});
		if (prev_infowindow_poly) {
			prev_infowindow_poly.close();
		}
		moveWithSlider(slider_idx);
	}

	if ($('.form-check-input[value="markers"]').is(':checked')) {
		$("#xDropdown").hide();
		$("#yDropdown").hide();
		$("#censusDropdownValue").hide();
		$("#censusDropdownX").hide();
		$("#censusDropdownY").hide();
		$("#transformX").hide();
		$("#transformY").hide();
		$("#chart1").hide();
		$("#chart2").show();
		$("#chart3").show();
		$("#chart4").hide();
		$('.play').hide()
		community_name = city;
		dateLabel();
		addCitySeries();
		census_opt = null;
		if (prev_infowindow_poly) {
		    prev_infowindow_poly.close();
		}
		if (map_heatmarks.length > 0) {
			removeHeatmap();
		}
		if (map_polygons.length > 0) {
			removePoly();
		}
		z = map.getZoom();
		console.log('z'+z)

		var zoom_ref = {}
		zoom_ref['chicago'] = {}
		zoom_ref['new_york'] = {}
		zoom_ref['baltimore'] = {}

		zoom_ref['chicago']['endpoint'] = {
			0: 'city_marker',
			1: 'district_marker',
			2: 'community_marker',
			3: 'beat_marker',
			4: 'incident_marker'
		} 

		zoom_ref['new_york']['endpoint'] = {
			0: 'city_marker',
			1: 'district_marker',
			2: 'precinct_marker',
			3: 'community_marker',
			4: 'incident_marker'
		} 

		zoom_ref['baltimore']['endpoint'] = {
			0: 'city_marker',
			1: 'district_marker',
			2: 'community_marker',
			3: 'ward_marker',
			4: 'incident_marker'
		} 

		zoom_ref['chicago']['field'] = {
			0: 'CITY',
			1: 'DIST_NUM',
			2: 'Community Area',
			3: 'BEAT_NUM',
			4: 'Location'
		} 

		zoom_ref['new_york']['field'] = {
			0: 'CITY',
			1: 'DIST_NUM',
			2: 'Precinct',
			3: 'Community Area',
			4: 'Location'
		} 

		zoom_ref['baltimore']['field'] = {
			0: 'CITY',
			1: 'DIST_NUM',
			2: 'Community Area',
			3: 'Ward',
			4: 'Location'
		} 

		if (z < 10) {
			var endpoint = zoom_ref[city]['endpoint'][0];
			field = zoom_ref[city]['field'][0];
		} else if (z == 10) {
			var endpoint = zoom_ref[city]['endpoint'][1];
			field = zoom_ref[city]['field'][1];
		} else if (z == 11 ) {
			var endpoint = zoom_ref[city]['endpoint'][2];
			field = zoom_ref[city]['field'][2];
		} else if (z == 12 ) {
			var endpoint = zoom_ref[city]['endpoint'][3];
			field = zoom_ref[city]['field'][3];
		} else {
			var endpoint = zoom_ref[city]['endpoint'][4];
			field = zoom_ref[city]['field'][4];
		}

		$.getJSON($SCRIPT_ROOT + '/' + endpoint + '/' + city + '/' + selected_dt, function(json) {
			res = json;
			createDropdownMarkers(res, field);
			dropDownSelect();

		});
		moveWithSlider(slider_idx);
	}
	
}

function moveWithSlider(slider_idx) {
	if (last_point) {
		last_point.update({marker: {fillColor: "#000000", lineWidth: 0, lineColor: "#000000", radius: 1}});
	}
	var this_point = $("#chart0").highcharts().series[0].data[slider_idx];
	this_point.update({marker: {fillColor: "#888888", lineWidth: 1, lineColor: "#000000", radius: 6}});
	last_point = this_point;
}

function dropDownSelect() {
	if ($('input[value="community"]').is(':checked')) {
		chartCensus();
		scatterCensus();
	}
	else if ($('input[value="markers"]').is(':checked')) {
		drawMarkers(res, field);
		chartCrimeTypes();
		chartCrimeLocations();
	}
}


function createDropdownMarkers(res, field) {
	$("#myDropdown").empty();
	p = new Set(Object.values(res.results['Primary Type']))

	for (index in Array.from(p)) {
		var value = Array.from(p)[index];
		var opt = document.createElement("option");
	    var t = document.createTextNode(value);
	    if (!crimetype_opt) {
		    if (index == 0) {
		    	opt.setAttribute("selected", "selected");
		    	crimetype_opt = value;
			  }
	    } else {
	    	if (value==crimetype_opt) {
	    		opt.setAttribute("selected", "selected");
	    	}
	    }
	    opt.setAttribute("value", "option" + index);
	    opt.appendChild(t);
		document.getElementById("myDropdown").appendChild(opt);
	}
	$("#myDropdown").show();
}



function createDropdownScatter(res) {
	$("#xDropdown").empty();
	$("#yDropdown").empty();
	p = new Set(Object.keys(res.results));
	var count = 0;

	for (index in Array.from(p)) {
		var value = Array.from(p)[index];
		var optX = document.createElement("option");
		var optY = document.createElement("option");
		if (['COMMUNITY', 'Community Area', 'GeoID', 'GEOG', 'COMMUNITY AREA NAME'].indexOf(value)==-1){
			    var xText = document.createTextNode(value);
			    var yText = document.createTextNode(value);
		
		    if (!scatterX) {
			    if (value == 'Avg. Annual Crimes') {
			    	optX.setAttribute("selected", "selected");
			    	scatterX = value;
				  }
		    } else {
		    	if (value==scatterX) {
		    		optX.setAttribute("selected", "selected");
		    	}
		    }
		    if (!scatterY) {
			    if ((count == 0) && (value != 'Avg. Annual Crimes')) {
			    	optY.setAttribute("selected", "selected");
			    	scatterY = value;
				} else if (count == 1){
				  	optY.setAttribute("selected", "selected");
			    	scatterY = value;
				}

		    } else {	
		    	if (value==scatterY) {
		    		optY.setAttribute("selected", "selected");
		    	}
		    }
		    optX.setAttribute("value", "option" + index);
		    optX.appendChild(xText);
			document.getElementById("xDropdown").appendChild(optX);
		    optY.setAttribute("value", "option" + index);
		    optY.appendChild(yText);
			document.getElementById("yDropdown").appendChild(optY);
			count += 1;
		}		
	}
	
	$("#chart4").show()
	$("#xDropdown").show();
	$("#yDropdown").show();
	if (city=='new_york'){
		$("#censusDropdownValue").show();
	}
	$("#censusDropdownX").show();
	$("#censusDropdownY").show();
	$("#transformX").show();
	$("#transformY").show();
}

function drawMarkers(res, field) {
	dt = res['selected_dt'];
	var labels = {}
	var bounds = {};
	removeMarkers();
	crimetype_opt = $("#myDropdown option:selected").text();
	
	for (index in res.results[dt]) {
		var value = res.results[dt][index];
		var comm_area = res.results[field][index];
		var primary_type = res.results['Primary Type'][index];
		var key = comm_area;
		if (primary_type==crimetype_opt) {
			if (!bounds.hasOwnProperty(key)) {
				bounds[key] = new google.maps.LatLngBounds();
				labels[key] = 0
			}
			bounds[key].extend(new google.maps.LatLng(res.results['Latitude'][index], res.results['Longitude'][index]));
			labels[key] += Number(res.results[dt][index]);
		}
	}

	$.each(bounds, function(index, bound) {
		var mark = new google.maps.Marker({
			position: bound.getCenter(),
			label: '',
			icon: {
				path: google.maps.SymbolPath.CIRCLE,
				fillOpacity: 0.4,
				strokeOpacity: 0.5,
				strokeWeight: 2,
				strokeColor: res.polyargs.stroke_color,
				fillColor: res.polyargs.fill_color,
				scale: (labels[index]/Math.sqrt(Math.min.apply(null, Object.values(labels)))+4) * z/12
			},
			map: map
		});
		mark.addListener('mouseover', hoverMarkers);
		mark.addListener('mouseout', unhoverMarkers);
		map_markers.push(mark);
		mark_labels = labels;
	// var markerCluster = new MarkerClusterer(map, map_markers);

	});    
}

function removeMarkers() {
	for(i = 0; i < map_markers.length; i++) {
		map_markers[i].setMap(null);
	}
	map_markers = [];
}

function hoverMarkers(event) {
	var idx = map_markers.indexOf(this);
	var r = getResults();
	var content = "<p>" + crimetype_opt + "</p><p>Gun crimes: " + Object.values(mark_labels)[idx] + "</p>";
	var position = this.getPosition()
	var infowindow = new google.maps.InfoWindow({content: content, position: new google.maps.LatLng(position.lat()+.0001, position.lng()) });
	infowindow.open(map);
	prev_infowindow_marker = infowindow;
}

function unhoverMarkers() {
    if (prev_infowindow_marker) {
        prev_infowindow_marker.close();
    }
}






function drawHeatmap(res) {
	if (res.results.hasOwnProperty(res.selected_dt)) {
		for(i = 0; i < Object.keys(res.results[res.selected_dt]).length; i++) {
			var lat_coord = res.results.Latitude[i];
			var lng_coord = res.results.Longitude[i];
			var incidents = res.results[selected_dt][i];
			var coords = new google.maps.LatLng(Number(lat_coord), Number(lng_coord));
			for (j = 0; j < Number(incidents); j++){
				map_heatmarks.push(coords);	
			}
		}

		heatmap = new google.maps.visualization.HeatmapLayer({
			          data: map_heatmarks,
			          map: map
		});
		heatmap.setMap(heatmap.getMap());
	}
}


function updateHeatmap(res) {
	if (res.results.hasOwnProperty(res.selected_dt)) {
		map_heatmarks = [];
		// add polygons
		for(i = 0; i < Object.keys(res.results[res.selected_dt]).length; i++) {
			var lat_coord = res.results.Latitude[i];
			var lng_coord = res.results.Longitude[i];
			var incidents = res.results[selected_dt][i];
			var coords = new google.maps.LatLng(Number(lat_coord), Number(lng_coord));
			for (j = 0; j < Number(incidents); j++){
				map_heatmarks.push(coords);	
			}
		}
		heatmap.setData(map_heatmarks);
	}
}

function removeHeatmap() {
	if (heatmap) {
		heatmap.setMap(null);
	}
	if (map_heatmarks) {
		map_heatmarks = [];
	}
}



function createDropdownPoly() {
	$("#myDropdown").empty();
	var indexes = []
	$.each(Object.keys(comm_data[community_id]), function(index, value) {
		if ($.inArray(value, ["adj_list", "COMMUNITY AREA NAME"]) == -1) { 
			indexes.push(index)
			var opt = document.createElement("option");
		    var t = document.createTextNode(value);
		    if (!census_opt) {
    		    if (index == Math.min.apply(null, indexes)) {
    		    	opt.setAttribute("selected", "selected");
    		    	census_opt = value;
    		    }
    		} else if (value==census_opt) {
    			opt.setAttribute("selected", "selected");
    		}
		    opt.setAttribute("value", "option" + index);
		    opt.appendChild(t);
			document.getElementById("myDropdown").appendChild(opt);
		}
	});
	
	$("#myDropdown").show();
	$("#chart1").show();
}

function chartCrimeTypes() {
	var data = [];
	var xLabels = [];
	$(function () {
		$.getJSON($SCRIPT_ROOT + '/crime_description/' + city + '/' + selected_dt, function(json) {
			$.each(json.results['Primary Type'], function(index, value) {
				if (value==crimetype_opt) {
					var name = json.results['Description'][index];
					var y = json.results[selected_dt][index];
					data.push({color: "#008080", y: y});
					xLabels.push(name);

				}
			});

		    // Build the chart
		    $('#chart2').highcharts({
		    	credits: {
					enabled: false
				},
		        chart: {
		            plotBackgroundColor: "#FFFFFF",
		            backgroundColor: null,
		            plotBorderWidth: null,
		            plotShadow: false,
		            type: 'bar',
		            plotBorderColor: "#373C44",
		            plotBorderWidth: 1
		        },
		        tooltip: {
		        	pointFormat: '<span style="color:{point.color}">\u25CF</span> {series.name}: <b>{point.y:,.0f}</b><br/>'
		        },
		        title: {
		            text: getMonthName(selected_dt).join('. ') + '<br>' + $("#myDropdown option:selected").text() + '<br>Gun Crimes by Sub-Type<br>',
		            style: {"fontSize": "14px"}

		        },
		        xAxis: {
		            categories: xLabels
		        },
		        yAxis: {
		        	title: {
		        		text: crimetype_opt + " CRIME COUNT"
		        	}
		        },
		      	series: [{
		      		name: 'CRIME COUNT',
		            showInLegend: false,
		            data: data,
		        }]
		    });
		});
	});
}

function chartCrimeLocations() {
	var data = [];
	var xLabels = [];
	$(function () {

		$.getJSON($SCRIPT_ROOT + '/crime_location/' + city + '/' + selected_dt, function(json) {
			$.each(json.results['Primary Type'], function(index, value) {
				if (value==crimetype_opt) {
					var name = json.results['Location Description'][index];
					var y = json.results[selected_dt][index];
					if (name.toString()!='0') {
						data.push({color: "#900C3F", y: y});
						xLabels.push(name);
					}
				}
			});

		    // Build the chart
		    $('#chart3').highcharts({
		    	credits: {
					enabled: false
				},
		        chart: {
		        	backgroundColor: null,
		            plotBackgroundColor: "#FFFFFF",
		            plotBorderWidth: null,
		            plotShadow: false,
		            type: 'bar',
		            plotBorderColor: "#373C44",
		            plotBorderWidth: 1
		        },
		        title: {
		            text: '<br>' + $("#myDropdown option:selected").text() + '<br>Gun Crimes by Location<br>',
		            style: {"fontSize": "14px"}
		        },
		        xAxis: {
		            categories: xLabels
		        },
		        yAxis: {
		        	title: {
		        		text: crimetype_opt + " CRIME COUNT"
		        	}
		        },
		      	series: [{
		      		name: 'CRIME COUNT',
		            showInLegend: false,
		            data: data,
		        }]
		    });
		});
	});
}



function chartCrimeSeries() {
	var data = [];
	var xLabels = [];
	$(function () {
		$.getJSON($SCRIPT_ROOT + '/trends/' + city , function(json) {
			for (month in json[city]) {
				var value = json[city][month];
				var data_point = {
								color: "#000000", 
								y: value, 
								marker: {radius: 1}
								};
				data.push(data_point);
				xLabels.push(month);
			}

		    // Build the chart
		    $('#chart0').highcharts({
		    	tooltip: {
				    crosshairs: true
				},
		    	credits: {
					enabled: false
				},
		        chart: {
		        	backgroundColor: null,
		            plotBackgroundColor: null,
		            plotBorderWidth: 0,
		            plotShadow: false,
		            type: 'line',
		        },
		        title: {
		            text: ''
		        },
		        xAxis: {
		            categories: xLabels
		        },
		        yAxis: {
		        	visible: false,
		        	enabled: false,
		        	title: {
		        		text: null
		        	}
		        },
		        plotOptions: {
		        	line: {
		        		color: "#000000"
		        	}

		        },
		      	series: [{
		      		name: 'CRIME COUNT',
		            showInLegend: false,
		            data: data,
    		        events: {
	                    click: function(event){
	                    	 $("#date-slider").val(event.point.x);
	                    	sliderOption();
	                    }
	                }
		        }]
		    });
		});
	});
}


function chartCensus() {
	census_opt = $("#myDropdown option:selected").text();
	var adj_list = comm_data[community_id]["adj_list"];
	var census_data = [];
	var census_labels = [];
	if (city=='chicago'){
		var all_point = comm_data["All"][census_opt];
		var all_data = [all_point];
	}
	census_data.push({color: "#C0C0C0", y: comm_data[community_id][census_opt]});
	census_labels.push(comm_data[community_id]["COMMUNITY AREA NAME"]);
	for (i in adj_list) {
		census_data.push({color: "#008080", y: comm_data[adj_list[i]][census_opt]});
		census_labels.push(comm_data[adj_list[i]]["COMMUNITY AREA NAME"]);
		if (city=='chicago'){
				all_data.push(all_point);
			}
	}

	series = [{
	        	type: "column",
	            name: census_opt,
	            data: census_data,
	            colorByPoint: true,
	            events: {
	                    click: function (event) {
	                    	community_name = event.point.category.toUpperCase();
	                    	var idx = Object.values(res.results['COMMUNITY']).indexOf(community_name.trim());

							community_id = res.results['Community Area'][idx].toString();
							if (prev_infowindow_poly) {
						        prev_infowindow_poly.close();
						    }
					        if (prev_poly) {
								prev_poly.setOptions({strokeColor: "#FFFFFF", strokeWeight: 0.5});
						    }
						    map_polygons[idx].setOptions({strokeColor: "#000000", strokeWeight: 1});
						    prev_poly = map_polygons[idx];
							createDropdownPoly();
							chartCensus();
							addCommunitySeries(community_id);
							dateLabel();	
	                    }
	                }
	        }]

	if (census_opt!="HARDSHIP INDEX" && city=="chicago") {
		series.push({
	        	type: "line",
	        	name: "CITY AVERAGE",
	        	data:  all_data,
	        	color: "#000000",
	        	marker: {
	        		enabled: false
	        	},
	        	tooltip: {
	        		headerFormat: "",
		            pointFormat: '{series.name}: <b>{point.y}</b><br/>'
		        }
	        })
	}

	if (censusChart) {
		censusChart.destroy()
	}

	if (city=='chicago') {
		var title_text = 'SOCIOECONOMIC CENSUS DATA 2008-2012';
	} else {
		title_text = 'CENSUS DATA 2010-2014';
	}
	$(function () {
	    censusChart = Highcharts.chart('chart1', {
	    	credits: {
					enabled: false
				},
			    chart: {
		            type: 'column',
			        plotBackgroundColor: "#FFFFFF",
		            backgroundColor: null,
		            plotShadow: false,
		            plotBorderColor: "#373C44",
		            plotBorderWidth: 1
		        },
		        legend: {
		            align: 'right',
		            verticalAlign: 'top',
		            layout: 'vertical',
		            floating: true,
		            x: 0,
		            y: 50
		        },
		        title: {
		            text: title_text,
		            style: {"fontSize": "14px"}
		        },
		        subtitle: {
		        	text: community_name + ': Compared with Adjacent Neighborhoods'
		        },
		        xAxis: {
		            categories: census_labels
		        },
		        yAxis: {
		            title: {
		                text: ""
		            }
		        },
		        series: series
	    });
	});
}


function transform(v, t) {
	if (t=="sqrt") {
		return Math.sqrt(v);
	} else if (t=="sqrd") {
		return Math.pow(v, 2);
	} else if (t=="log") {
		return Math.log(v);
	} else {
		return v;
	}
}

function scatterCensus() {
	var values = $("#valueDropdown option:selected").text();

	$.getJSON($SCRIPT_ROOT + '/census_correlation/' + city + '/' + values, function(json) {
		var series = []

		scatterX = $("#xDropdown option:selected").text();
		scatterY = $("#yDropdown option:selected").text();
		var transformX = $("#xTransform").val();
		var transformY = $("#yTransform").val();
		
		var corrX = [];
		var corrY = []

		createDropdownScatter(json);
		for (index in json.results[scatterX]) {
			var scatter_x = json.results[scatterX][index]
			var scatter_y = json.results[scatterY][index];
			var label = json.results['COMMUNITY'][index];
			if (label == community_name) {
				var color = "#FF0000";
				var zIndex = 100;
				var symbol = 'diamond';
				var radius = 6
			} else {
				var color = "#808080";
				var zIndex = 0;
				var symbol = 'circle';
				var radius = 4;
			}
			if (scatter_x>0 && scatter_y>0) {
				scatter_x = transform(scatter_x, transformX);
				scatter_y = transform(scatter_y, transformY);

				series.push({data: [[scatter_x, scatter_y]], 
							color: color, 
							name: label, 
							marker: {symbol: symbol, radius: radius}, 
							zIndex: zIndex});
				corrX.push(scatter_x);
				corrY.push(scatter_y);
			}
		}
		var corr_coeff = jStat.corrcoeff(corrX, corrY);

		$(function () {
		    cencsusScatter = Highcharts.chart('chart4', {
		    	credits: {
						enabled: false
					},
				    chart: {
			            type: 'scatter',
			            plotBackgroundColor: "#FFFFFF",
			            backgroundColor: null,
			            plotShadow: false,
			            plotBorderColor: "#373C44",
			            plotBorderWidth: 1
			        },
			        legend: {
			        	enabled: false
			        },
			        xAxis: {
			        	enabled: true,
			        	title: {
			        		text: scatterX
			        	}
			        },
			        yAxis: {
			        	enabled: true,
			        	title: {
			        		text: scatterY
			        	}
			        },
			        title: {
			            text: 'CENSUS DATA 2010-2014',
			            style: {"fontSize": "14px"}
			        },
			        subtitle: {
			        	text: 'Correlation Coefficient: '+ Math.round(corr_coeff*100) + '%',
			        	style: {"fontSize": "12px"}
			        },
			        tooltip: {
			        	pointFormat: 'X: <b>{point.x:,.0f}</b><br>Y: <b>{point.y:,.0f}</b><br/>' 
			        },
			        series: series
			});
		});
	});
}

function drawPoly(res) {
	if (res.results.hasOwnProperty(res.selected_dt)) {

		// add polygons
		for(i = 0; i < Object.keys(res.results[res.selected_dt]).length; i++) {
			var path_len = res.results.the_geom_community[i].length;
			polypaths[i] = []
			for (j = 0; j < path_len; j++){
				var lat_coord = res.results.the_geom_community[i][j][0];
				var lng_coord = res.results.the_geom_community[i][j][1];
				var coords = new google.maps.LatLng(Number(lat_coord), Number(lng_coord));
				polypaths[i].push(coords);
			}

		    map_polygons[i] = new google.maps.Polygon({
		        strokeColor: res.polyargs.stroke_color,
		        strokeOpacity: res.polyargs.stroke_opacity,
		        strokeWeight: res.polyargs.stroke_weight,
		        fillOpacity: res.polyargs.fill_opacity,
		        fillColor: res.results.fill_color[i],
		        path: polypaths[i],
		        map: map,
		        geodesic: true
		    });
		    map_polygons[i].setMap(map);
		    map_polygons[i].addListener('mouseover', hoverPoly);
		    map_polygons[i].addListener('mouseout', function() {
		    	unhoverPoly(this);
		    });
		    map_polygons[i].addListener('click', clickPoly);
	    }
	}
}


function updatePoly(res) {
	if (res.results.hasOwnProperty(res.selected_dt)) {

		// add polygons
		for(i = 0; i < map_polygons.length; i++) {
			map_polygons[i].setOptions({fillColor: res.results.fill_color[i]});
		}
	}
}

function removePoly() {
	for(i = 0; i < map_polygons.length; i++) {
		map_polygons[i].setMap(null);
	}
	map_polygons = [];
}

function clickPoly(event) {
	var latlngclicked = event.latLng;
	var idx = map_polygons.indexOf(this);
	var r = getResults();

	community_name = r.results.COMMUNITY[idx];

	community_id = r.results['Community Area'][idx].toString() 
	var content = "<p>" + r.results.COMMUNITY[idx] + "</p><p>Gun crimes: " + r.results[selected_dt][idx] + "</p>";
	var infowindow = new google.maps.InfoWindow({content: content, position: latlngclicked});
	if (prev_infowindow_poly) {
        prev_infowindow_poly.close();
    }
    if (prev_poly) {
		prev_poly.setOptions({strokeColor: "#FFFFFF", strokeWeight: 0.5});
    } 
	this.setOptions({strokeColor: "#000000", strokeWeight: 1});
    infowindow.open(map);
	prev_infowindow_poly = infowindow;
	prev_poly = this;
	createDropdownPoly();
	chartCensus();
	scatterCensus();
	addCommunitySeries(community_id);
	dateLabel();
}

function addCommunitySeries(community_id) {
	$.getJSON($SCRIPT_ROOT + "/community_trends/" + city + "/" + community_id.replace('/', '%2F'), function(json) {
		var data = [];
		data = Object.values(json.results);
		$("#chart0").highcharts().series[0].setData(data);		
	});
}

function addCitySeries() {
	$.getJSON($SCRIPT_ROOT + "/trends/" + city, function(json) {
		var data = [];
		data = Object.values(json[city]);
		$("#chart0").highcharts().series[0].setData(data);		
	});
}


function hoverPoly() {
	this.setOptions({fillOpacity: 1});
}

function unhoverPoly(p) {
	var idx = map_polygons.indexOf(p);
	p.setOptions({fillOpacity: res.polyargs.fill_opacity});
}



function getResults() {
	return res;
}


function getSelectedDt() {
	return selected_dt;
}



