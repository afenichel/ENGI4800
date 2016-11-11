var selected_dt;
var res = {};
var latlngclicked;
var polypaths = [];
var map = null;
var heatmap = null;
var prev_infowindow_map = null;
var map_polygons = [];
var map_heatmarks = [];

var city = $("meta[name='city']").attr("content"); 
var date_dropdown = $("meta[name='date_dropdown']").attr("content").replace(/\[|\]|'/g, "").split(", ")

$.getJSON($SCRIPT_ROOT + '/community/' + city + '/0', function(json) {
		res = json;
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
	
	if (map_polygons.length > 0) {
    	removePoly();
    }
    if (map_heatmarks.length > 0) {
    	removeHeatmap();
    }
	if ($('input[value="community"]').is(':checked') && $("myDropdown option:selected").val()!="0") {
		$.getJSON($SCRIPT_ROOT + '/community/' + city + '/' + selected_dt, function(json) {
			res = json;
			drawPoly(res);
		});
	}
	if ($('input[value="heatmap"]').is(':checked') && $("myDropdown option:selected").val()!="0") {
		$.getJSON($SCRIPT_ROOT + '/heatmap/' + city + '/' + selected_dt, function(json) {
			res = json;
			drawHeatmap(res);
		});
	}
}



function initMap() {
    document.getElementById('view-side').style.display = 'block';
    map = new google.maps.Map(
    document.getElementById('view-side'), {
        center: new google.maps.LatLng(res.map_dict.center[0], res.map_dict.center[1]),
        zoom: res.map_dict.zoom,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        zoomControl: res.map_dict.zoom_control,
        mapTypeControl: res.map_dict.maptype_control,
        scaleControl: true,
        streetViewControl: res.map_dict.streetview_control,
        rotateControl: res.map_dict.rorate_control,
        scrollwheel: res.map_dict.scroll_wheel,
        fullscreenControl: res.map_dict.fullscreen_control
    });
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

function removeHeatmap() {
	if (heatmap) {
		heatmap.setMap(null);
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
		    map_polygons[i].addListener('click', function(event) {
		    	latlngclicked = event.latLng;
		    	var idx = map_polygons.indexOf(this);
				var content = "<p>" + res.results.COMMUNITY[idx] + "</p><p>Gun crimes: " + res.results[selected_dt][idx] + "</p>";
				var infowindow = new google.maps.InfoWindow({content: content, position: latlngclicked});

			    if (prev_infowindow_map) {
		            prev_infowindow_map.close();
		        }
	        	infowindow.open(map);
	        	prev_infowindow_map = infowindow;		    	
		    });
	    }
	}
}


function removePoly() {
	for(i = 0; i < map_polygons.length; i++) {
		map_polygons[i].setMap(null);
	}
}

function hoverPoly() {
	this.setOptions({fillOpacity: 1});
}

function unhoverPoly(p) {
	var idx = map_polygons.indexOf(p);
	p.setOptions({fillOpacity: res.results.fill_opacity[idx]});
}



function changeOption() {
    selected_dt = document.getElementById("myDropdown").value;
    if (map_polygons.length > 0) {
    	removePoly();
    }
    if (map_heatmarks.length > 0) {
    	removeHeatmap();
    }
	if ($('input[value="community"]').is(':checked') && $("myDropdown option:selected").val()!="0") {
		$.getJSON($SCRIPT_ROOT + '/community/' + city + '/' + selected_dt, function(json) {
			res = json;
			drawPoly(res);
		});
	}
	if ($('input[value="heatmap"]').is(':checked') && $("myDropdown option:selected").val()!="0") {
		$.getJSON($SCRIPT_ROOT + '/heatmap/' + city + '/' + selected_dt, function(json) {
			res = json;
			drawHeatmap(res);
		});
	}
}

