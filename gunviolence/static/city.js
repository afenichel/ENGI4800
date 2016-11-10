var selected_dt;
var res = {};
var latlngclicked;
var polypaths = [];
var map = null;
var prev_infowindow_map = null;
var map_polygons = [];
// var map_markers = [];
// var map_rectangles = [];
// var map_circles = [];
// var map_polylines = [];

var city = $("meta[name='city']").attr("content"); 

console.log(city);

$.getJSON($SCRIPT_ROOT + '/' + city + '/0', function(json) {
		res = json;
	});
console.log(res);
google.maps.event.addDomListener(window, 'load', initialize_map);



function changeOption() {
    selected_dt = document.getElementById("myDropdown").value;
	console.log(selected_dt);
	$.getJSON($SCRIPT_ROOT + '/' + city + '/' + selected_dt, function(json) {
		res = json;
		console.log(res['map_dict']);
		if (polypaths.length>0){
			removePoly(res);
		}
		drawPoly(res);
	});

}



function initialize_map() {
    document.getElementById('view-side').style.display = 'block';
    console.log(res.map_dict)
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

function removePoly(res) {
	for(i = 0; i < Object.keys(res.results[res.selected_dt]).length; i++) {
		map_polygons[i].setMap(null);
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
				var content = res.results.COMMUNITY[idx];
				var infowindow = new google.maps.InfoWindow({content: content, position: latlngclicked});
			    if (prev_infowindow_map) {
		    		console.log(prev_infowindow_map);
		            prev_infowindow_map.close();
		        }
	        	infowindow.open(map);
	        	prev_infowindow_map = infowindow;		    	
		    });
	    }
	}
}



function getInfoCallback(map, p) {

    return function(ev) {
        
        
    };
}


function hoverPoly() {
	this.setOptions({fillOpacity: 1});
}

function unhoverPoly(p) {
	var idx = map_polygons.indexOf(p);
	p.setOptions({fillOpacity: res.results.fill_opacity[idx]});
}

// function addPoly() {
//         flightPath.setMap(map);
//       }
//     // add gmap markers
//     var raw_markers = [];
//     for(i=0; i<0;i++) {
//         map_markers[i] = new google.maps.Marker({
//             position: new google.maps.LatLng(raw_markers[i].lat, raw_markers[i].lng),
//             map: map,
//             icon: raw_markers[i].icon,
//             title: raw_markers[i].title ? raw_markers[i].title : null
//         });

//        if(raw_markers[i].infobox)
//        {
//             google.maps.event.addListener(
//                     map_markers[i],
//                     'click',
//                     getInfoCallback(map, raw_markers[i].infobox)
//             );
//        }
//     }

//     // add rectangles
//     var raw_rectangles = [];
//     for(i = 0; i < 0; i++) {
//         map_rectangles[i] = new google.maps.Rectangle({
//             strokeColor: raw_rectangles[i].stroke_color,
//             strokeOpacity: raw_rectangles[i].stroke_opacity,
//             strokeWeight: raw_rectangles[i].stroke_weight,
//             fillColor: raw_rectangles[i].fill_color,
//             fillOpacity: raw_rectangles[i].fill_opacity,
//             map: map,
//             bounds: {
//                 north: raw_rectangles[i].bounds.north,
//                 east: raw_rectangles[i].bounds.east,
//                 south: raw_rectangles[i].bounds.south,
//                 west: raw_rectangles[i].bounds.west },
//         });

//        if(raw_rectangles[i].infobox)
//        {
//             google.maps.event.addListener(
//                     map_rectangles[i],
//                     'click',
//                     getInfoCallback(map, raw_rectangles[i].infobox)
//             );
//        }
//     }

//     // add circles
//     var raw_circles = [];
//     for(i = 0; i < 0; i++) {
//         map_circles[i] = new google.maps.Circle({
//             strokeColor: raw_circles[i].stroke_color,
//             strokeOpacity: raw_circles[i].stroke_opacity,
//             strokeWeight: raw_circles[i].stroke_weight,
//             fillColor: raw_circles[i].fill_color,
//             fillOpacity: raw_circles[i].fill_opacity,
//             map: map,
//             center: {
//                 lat: raw_circles[i].center.lat,
//                 lng: raw_circles[i].center.lng,
//             },
//             radius: raw_circles[i].radius
//         });

//        if(raw_circles[i].infobox)
//        {
//             google.maps.event.addListener(
//                     map_circles[i],
//                     'click',
//                     getInfoCallback(map, raw_circles[i].infobox)
//             );
//        }
//     }

//     // add polylines
//     var raw_polylines = [];
//     for(i = 0; i < 0; i++) {
//         map_polylines[i] = new google.maps.Polyline({
//             strokeColor: raw_polylines[i].stroke_color,
//             strokeOpacity: raw_polylines[i].stroke_opacity,
//             strokeWeight: raw_polylines[i].stroke_weight,
//             path: raw_polylines[i].path,
//             map: map,
//             geodesic: true
//         });

//        if(raw_polylines[i].infobox)
//        {
//             google.maps.event.addListener(
//                     map_polylines[i],
//                     'click',
//                     getInfoCallback(map, raw_polylines[i].infobox)
//             );
//        }
//     }


