function close_btn(e) { //close the flash message
	console.log(e);
	var parent_div = e.parentElement;
	if (typeof (parent_div) != 'undefined' && parent_div != null) {
		// parent_div.innerHTML = "";
		console.log('closing flash message...');
		parent_div.remove();
	} else {
		var parent_div = document.getElementById('flash-msg').children[0];
		if (typeof (parent_div) != 'undefined' && parent_div != null) {
			console.log('closing flash message...');
			parent_div.remove();
		};
	};
};

// $(document).ready(function () {
var form = document.getElementById('input-form');
if (form !== null) {
	$('[data-toggle="tooltip"]').tooltip({
		delay: {show: 50, hide: 100},
		placement: "bottom",
		effect: "fade",
		opacity: 0.7
	}
	);
};

// function flash_msg(msg) {
// 	var str_msg =
// 		`
// 		<div class="col-6" id="flash-msg">
// 			<div>
// 				<span id="warning-msg"><strong>${msg}</strong></span>
// 				<button onclick="close_btn(this)" type="button" class="close" aria-label="Close">
// 					<span aria-hidden="true">&times;</span>
// 				</button>
// 			</div>
// 		</div>
// 		`;
// 	document.getElementById("tsl-panel").insertAdjacentHTML('afterbegin', str_msg);
// };


// function inject_tsl_view() {
// 	var rack1 = document.forms[1]["rack1"].value;
// 	var rack2 = document.forms[1]["rack2"].value;
// 	console.log(rack1);
// 	console.log(rack2);
// 	$.ajax({
// 		url: '/es/combine-worklists',
// 		data: {
// 			input_rack_id1: rack1,
// 			input_rack_id2: rack2
// 		},
// 		dataType: 'json'
// 	})
// 		.done((res) => {
// 			if (rack1 == "" || rack1 == null, rack2 == "" || rack2 == null) {
// 				console.log('missing');
// 				flash_msg(res.row_data);
// 			} else {
// 				document.getElementById("tsl-panel").innerHTML = res.tsl_html;
// 			};
// 		})
// 		.fail((err) => {
// 			console.log(err);
// 		});
// };

function switch_tabs(navbar) {
	if (navbar === $("#wl-navbar")[0]) {
		navbar.className = "nav-link active";
		document.getElementById("log-navbar").className = "nav-link";
		var flash_msg_xbtn = document.getElementsByClassName("close");
		if (typeof (flash_msg_xbtn) != 'undefined' && flash_msg_xbtn != null) {
			console.log('closing flash msg in worklist combine tab');
			close_btn(flash_msg_xbtn);
		};
	} else {
		navbar.className = "nav-link active";
		document.getElementById("wl-navbar").className = "nav-link";
		var flash_msg_xbtn = document.getElementsByClassName("close");
		if (typeof (flash_msg_xbtn) != 'undefined' && flash_msg_xbtn != null) {
			console.log('closing flash msg in logs tab');
			close_btn(flash_msg_xbtn);
		};
	};
};

// function switch_tabs(navbar, url) {
// 	// console.log(navbar);
// 	$.ajax({url: url})
// 		.done((res) => {
// 			$("#output").html(res);
// 			if (navbar === $("#wl-navbar")[0]) {
// 				navbar.className = "nav-link active";
// 				document.getElementById("log-navbar").className = "nav-link";
// 				document.getElementById("input-form").style.display = "none";
// 				document.getElementById("submit-row").style.display = "none";
// 				var flash_msg_xbtn = document.getElementsByClassName("close");
// 				if (typeof (flash_msg_xbtn) != 'undefined' && flash_msg_xbtn != null) {
// 					console.log('closing flash msg in worklist combine tab');
// 					close_btn(flash_msg_xbtn);
// 				};
// 			} else {
// 				navbar.className = "nav-link active";
// 				document.getElementById("wl-navbar").className = "nav-link";
// 				document.getElementById("input-form").style.display = "block";
// 				document.getElementById("submit-row").style.display = "block";
// 				var flash_msg_xbtn = document.getElementsByClassName("close");
// 				if (typeof (flash_msg_xbtn) != 'undefined' && flash_msg_xbtn != null) {
// 					console.log('closing flash msg in logs tab');
// 					close_btn(flash_msg_xbtn);
// 				};
// 			};
// 		})
// 		.fail((err) => {
// 			console.log(err);
// 		});
// };


// remove stupid plotly logo since setting in config param didn't work
// var list = document.getElementsByClassName('modebar modebar--hover ease-bg');
// list[0].removeChild(list[0].childNodes[4]);


// function basic_popup(url) {
// 	popup_window = window.open(url, 'popUpWindow', 'height=600,width=900,left=20,top=20,resizable=yes,scrollbars=yes,toolbar=yes,menubar=no,location=no,directories=no, status=yes');
// 	console.log('clicked!');
// }
function extract_proj_sw(self) {
	let elem_id = self.id;
	// let current_idx = elem_id.substring(elem_id.length - 1, elem_id.length);
	var split_array = elem_id.split("-");
	current_idx = split_array[split_array.length - 1];
	console.log(current_idx);
	let current_sample_well = `sample-well-group-${current_idx}`

	let proj_id_val = document.getElementById(`project-id-group-${current_idx}`).innerText;
	let sample_well_val = document.getElementById(current_sample_well).innerText;
	// console.log(proj_id_val);
	// console.log(sample_well_val);
	return [proj_id_val, sample_well_val];
};

function popup_center(self, host, db_type, w, h) {
	let data_array = extract_proj_sw(self);
	console.log(data_array[0]);
	console.log(data_array[1]);
	let url = `http://${host}:8003/${db_type}/uvplot/${data_array[0]}/${data_array[1]}`;
	console.log(url);
	var left = (screen.width / 2) - (w / 2);
	var top = (screen.height / 2) - (h / 2);
	return window.open(url, '_blank', 'toolbar=no, location=no, directories=no, status=no, menubar=no, scrollbars=yes, resizable=yes, copyhistory=no, width=' + w + ', height=' + h + ', top=' + top + ', left=' + left);
};
