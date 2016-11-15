var selected_dt;
var res = {};
var comm_data = {};
var polypaths = [];
var map = null;
var heatmap = null;
var prev_infowindow_map = null;
var map_polygons = [];
var map_heatmarks = [];
var map_markers = [];
var city = $("meta[name='city']").attr("content"); 
var date_dropdown = $("meta[name='date_dropdown']").attr("content").replace(/\[|\]|'/g, "").split(", ")
var community_name;
var community_id;
var censusChart;
var census_opt;
var crimetype_opt;
var field;
var z;

$.getJSON($SCRIPT_ROOT + '/community/' + city + '/0', function(json) {
		res = json;
	});


$.getJSON($SCRIPT_ROOT + '/census/' + city , function(json) {
		comm_data = json;
	});

google.maps.event.addDomListener(window, 'load', initMap);

function sliderOption() {
	var slider_idx = $("#date-slider").val();
	selected_dt = date_dropdown[slider_idx];

	var dt = document.getElementById("date-label");
	var yr = selected_dt.split("-")[0];
	var m = selected_dt.split("-")[1] - 1;
	var dt_obj = new Date(yr, m);
	var monthName = dt_obj.toString().split(" ")[1];
	dt.innerHTML = "Date: " + monthName + " " + yr;


	if ($('input[value="community"]').is(':checked')) {
		console.log($("#chart1").is(":visible"))
		$.getJSON($SCRIPT_ROOT + '/community/' + city + '/' + selected_dt, function(json) {
			res = json;
			if (map_polygons.length > 0) {
		    	updatePoly(res);
		    }
		    else {
				drawPoly(res);
		    }
	        if (map_heatmarks.length > 0) {
		    	removeHeatmap();
		    }
			if (prev_infowindow_map) {
				comm_idx = Object.values(res.results.COMMUNITY).indexOf(community_name);
				var content = "<p>" + res.results.COMMUNITY[comm_idx] + "</p><p>Gun crimes: " + res.results[selected_dt][comm_idx] + "</p>";
				prev_infowindow_map.setContent(content);
			}
		});
	}
	if ($('input[value="heatmap"]').is(':checked')) {
		$.getJSON($SCRIPT_ROOT + '/heatmap/' + city + '/' + selected_dt, function(json) {
			res = json;
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
		if (prev_infowindow_map) {
			prev_infowindow_map.close();
		}
		$("#myDropdown").hide();
		$("#chart1").hide();
	}
	if ($('input[value="markers"]').is(':checked')) {
		z = map.getZoom();

			if (map_heatmarks.length > 0) {
				removeHeatmap();
			}
			if (map_polygons.length > 0) {
				removePoly();
			}
		z = map.getZoom();
		console.log('z'+z)
		if (z < 11) {
			var endpoint = 'district_marker';
			field = 'DIST_NUM';
		} else if (z == 11 ) {
			var endpoint = 'community_marker';
			field = 'Community Area';
		} else if (z == 12 ) {
			var endpoint = 'beat_marker';
			field = 'BEAT_NUM'
		} else {
			var endpoint = 'incident_marker';
			field = 'Location'
		}
		console.log($SCRIPT_ROOT + '/' + endpoint + '/' + city + '/' + selected_dt);
		$.getJSON($SCRIPT_ROOT + '/' + endpoint + '/' + city + '/' + selected_dt, function(json) {
			res = json;
			createDropdownMarkers(res, field);
			drawMarkers(res, field);
		});
	}
}


function createDropdownMarkers(res, field) {
	$("#myDropdown").empty();
	p = new Set(Object.values(res.results['Primary Type']))
	console.log(Array.from(p));
	$.each(Array.from(p), function(index, value) {
		console.log(value);
		var opt = document.createElement("option");
	    var t = document.createTextNode(value);
	    if (index == 0) {
	    	opt.setAttribute("selected", "selected");
	    	crimetype_opt = value;
	    }
	    opt.setAttribute("value", "option" + index);
	    opt.appendChild(t);
		document.getElementById("myDropdown").appendChild(opt);
	});
	$("#myDropdown").show();
}




function drawMarkers(res, field) {
	dt = res['selected_dt'];
	console.log(dt);
	var labels = {}
	var bounds = {};


	for(i = 0; i < map_markers.length; i++) {
		map_markers[i].setMap(null);
	}

	$.each(res.results[dt], function(index, value) {
		var comm_area = res.results[field][index];
		var primary_type = res.results['Primary Type'][index];
		var key = [comm_area, primary_type]
		if (primary_type==crimetype_opt) {
			if (~map_markers.hasOwnProperty(key)) {
				bounds[key] = new google.maps.LatLngBounds();
				labels[key] = 0
			}
			bounds[key].extend(new google.maps.LatLng(res.results['Latitude'][index], res.results['Longitude'][index]));
			labels[key] += res.results[dt][index];
		}
	});
	console.log('LENGTH '+Object.keys(bounds).length);
	$.each(bounds, function(index, bound) {
		var mark = new google.maps.Marker({
			position: bound.getCenter(),
			label: labels[index].toString(),
			icon: {
				path: google.maps.SymbolPath.CIRCLE,
				fillOpacity: 0.3,
				strokeOpacity: 0.5,
				strokeWeight: 2,
				strokeColor: res.polyargs.stroke_color,
				fillColor: res.polyargs.fill_color,
				scale: 10
			},
			map: map
		});
		map_markers.push(mark) 
	});    
}

function updatePoly(res) {
	if (res.results.hasOwnProperty(res.selected_dt)) {

		// add polygons
		for(i = 0; i < map_polygons.length; i++) {
			map_polygons[i].setOptions({fillOpacity: res.results.fill_opacity[i]});
		}
	}
}



function initMap() {
	$("#myDropdown").hide();
	z = res.map_dict.maptype_control;
    document.getElementById('view-side').style.display = 'block';
    map = new google.maps.Map(
    document.getElementById('view-side'), {
        center: new google.maps.LatLng(res.map_dict.center[0], res.map_dict.center[1]),
        zoom: res.map_dict.zoom,
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
		if (prev_infowindow_map) {
			prev_infowindow_map.close();
		}
	})
	map.addListener('zoom_changed', sliderOption);
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
		        fillOpacity: res.results.fill_opacity[i],
		        fillColor: res.polyargs.fill_color,
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



function clickPoly(event) {
	var latlngclicked = event.latLng;
	var idx = map_polygons.indexOf(this);
	var r = getResults();
	community_name = r.results.COMMUNITY[idx];
	community_id = r.results['Community Area'][idx].toString() 
	var content = "<p>" + r.results.COMMUNITY[idx] + "</p><p>Gun crimes: " + r.results[selected_dt][idx] + "</p>";
	var infowindow = new google.maps.InfoWindow({content: content, position: latlngclicked});

    if (prev_infowindow_map) {
        prev_infowindow_map.close();
    }
	infowindow.open(map);
	prev_infowindow_map = infowindow;
	createDropdownCharts();
	chartCensus();
	
}

function createDropdownCharts() {
	$("#myDropdown").empty();
	$.each(Object.keys(comm_data[community_id]), function(index, value) {
		if ($.inArray(value, ["adj_list", "COMMUNITY AREA NAME"]) == -1) { 
			var opt = document.createElement("option");
		    var t = document.createTextNode(value);
		    if (index == 0) {
		    	opt.setAttribute("selected", "selected");
		    	census_opt = value;
		    }
		    opt.setAttribute("value", "option" + index);
		    opt.appendChild(t);
			document.getElementById("myDropdown").appendChild(opt);
		}
	});
	$("#myDropdown").show();
	$("#chart1").show();

}

function dropDownSelect() {
	if ($('input[value="community"]').is(':checked')) {
		chartCensus();
	}
	else if ($('input[value="markers"]').is(':checked')) {
		drawMarkers(res, field);
	}
}

function chartCensus() {
	census_opt = $("#myDropdown option:selected").text();
	var adj_list = comm_data[community_id]["adj_list"];
	var census_data = [];
	var census_labels = [];
	var all_point = comm_data["All"][census_opt]
	var all_data = [all_point];
	census_data.push({color: "#C0C0C0", y: comm_data[community_id][census_opt]});
	census_labels.push(comm_data[community_id]["COMMUNITY AREA NAME"]);
	for (i in adj_list) {
		census_data.push(comm_data[adj_list[i]][census_opt]);
		census_labels.push(comm_data[adj_list[i]]["COMMUNITY AREA NAME"]);
		all_data.push(all_point);
	}

	series = [{
	        	type: "column",
	            name: census_opt,
	            data: census_data
	        }]

	if (census_opt!="HARDSHIP INDEX") {
		series.push({
	        	type: "line",
	        	name: "City Average",
	        	data:  all_data
	        })
	}

	if (censusChart) {
		censusChart.destroy()
	}
	$(function () {
	    censusChart = Highcharts.chart('chart1', {
	    chart: {
	            type: 'column'
	        },
	        title: {
	            text: 'Census Data'
	        },
	        subtitle: {
	        	text: 'Compared with Adjacent Neighborhoods'
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


function getResults() {
	return res;
}


function getSelectedDt() {
	return selected_dt;
}

function removePoly() {
	for(i = 0; i < map_polygons.length; i++) {
		map_polygons[i].setMap(null);
	}
	map_polygons = [];
}

function hoverPoly() {
	this.setOptions({fillOpacity: 1});
}

function unhoverPoly(p) {
	var idx = map_polygons.indexOf(p);
	p.setOptions({fillOpacity: res.results.fill_opacity[idx]});
}




