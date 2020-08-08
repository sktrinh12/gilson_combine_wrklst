function close_btn() { //close the flash message
	var flash_msg = document.getElementById("flash-msg");
	flash_msg.innerHTML = "";
};

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
