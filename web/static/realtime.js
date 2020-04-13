$(() => {

    let props = {
	planarAngle: 0,
	zAngle: 0,
	x: -1,
	y: 0,
	z: 0,
	color: "#000",
	text: "",
	launchStrength: 0.1,
    };
    window.arrowProps = props;

    window.ws = new WebSocket(`ws://${location.host}/realtime/`);

    function send(msg) {
	ws.send(JSON.stringify(msg));
    }

    ws.onclose = () => {
	window.ws = new WebSocket(`ws://${location.host}/realtime/`);
    };
    ws.onready = () => {
	/*send({
	    "action": "join",
	    "props": props
	});*/
    }

    let sendUpdate = _.throttle(() => {
	send({
	    "action": "update",
	    "props": props
	});
    }, 50)

    Math.clamp=function(a,b,c){ return Math.max(b,Math.min(c,a)); }

    function updateArrow(skipSendingUpdate) {
	let x = props.x = Math.clamp(props.x, -1, 1);
	let y = props.y = Math.clamp(props.y, -1, 1);
	let z = props.z = Math.clamp(props.z, -1, 1);
	props.planarAngle = Math.clamp(props.planarAngle, -89, 89);
	props.zAngle = Math.clamp(props.zAngle, -89, 89);

	if (Math.abs(x) != 1 && Math.abs(y) != 1) {
	    if (Math.abs(x) > Math.abs(y)) {
		x = x > 0 ? 1 : -1;
	    } else {
		y = y > 0 ? 1 : -1;
	    }
	}

	let angle = props.planarAngle + 90;
	if (x == 1) {
	    angle += 180;
	}
	if (y == 1) {
	    angle -= 90;
	} else if (y == -1) {
	    angle += 90;
	}

	let scale = (z + 4) / 4;
	let boxscale = (-z + 8) / 8;

	$("#arrow").css("transform", `rotateZ(${angle}deg) rotateX(${props.zAngle}deg) scale(${scale})`);
	$("#box").css("transform", `scale(${boxscale})`);
	$("#arrow").css("top", `${y * 100 + 150}px`);
	$("#arrow").css("left", `${x * 100 + 150}px`);
	$("#arrow polygon").attr("fill", props.color);
	$("#launch, #text").css("color", props.color);

	$("#arrow").css({
	    "marginTop": y == -1 ? "-50px" : Math.abs(x) == 1 ? "-25px" : "0",
	    "marginLeft": x == -1 ? "-50px" : Math.abs(y) == 1 ? "-25px" : "0",
	    "marginRight": x == 1 ? "-50px" : "0",
	});

	$("#angle").val(props.planarAngle);
	$("#z").val(props.z);

	if (!skipSendingUpdate) {
	    sendUpdate();
	}
    }

    updateArrow(true);

    $("input").on("input", function() {
	if ($(this).prop("id") == "text" &&
	    $(this).val().indexOf(" ") != -1) {
	    alert("Please write only a single word!");
	    return false;
	}

	props[$(this).prop("id")] = $(this).val();
	updateArrow();
    });

    let i = interact($('#interact-area')[0]).gesturable({
	listeners: {
	    move (event) {
		props.planarAngle += event.da;
		props.z += Math.log(event.scale) / 100;
		updateArrow();
	    }
	}
    }).draggable({
	listeners: {
	    move (event) {
		props.x += event.dx / 100;
		props.y += event.dy / 100;
		updateArrow();
	    },
	}
    });

    function updateLaunchStrength() {
	if (!$("#launch").data("launchStart")) { return false; }
	let dt = new Date().getTime() - $("#launch").data("launchStart");
	props.launchStrength = Math.clamp(Math.pow(dt / 5000, .5), 0.1, 1);
	$("#launch").css("transform", `scale(${props.launchStrength * 2})`);
	requestAnimationFrame(updateLaunchStrength);
    }

    $("#launch").on("mousedown touchstart", function(e) {
	$(this).data("launchStart", new Date().getTime());
	updateLaunchStrength();
    });

    $("#launch").on("mouseup touchend", function(e) {
	$(this).data("launchStart", null);
	$(this).css("transform", "");

	if (!props.text) {
	    alert("Please enter a word!");
	    return false;
	}

	send({
	    "action": "launch",
	    "props": props,
	    "strength": $(this).data("launchStrength"),
	});

	$("#launchedModal").modal("show");
	$("#continueButton").prop("disabled", true);
	setTimeout(() => {
	    $("#continueButton").prop("disabled", false);
	}, 2000);
    });

    $("#continueButton").click(sendUpdate);
});
