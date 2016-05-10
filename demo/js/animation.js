var arrowsup = ["#aup1","#aup2","#aup3","#aup4","#aup5","#aup6"];
var arrowsdown = ["#adown1","#adown2","#adown3","#adown4","#adown5","#adown6"];
var switches = ["#s1","#s2","#s3","#s4","#s5","#s6"];
var links = ["#link12","#link23","#link36","#link14","#link45","#link56"];
var hosts = ["#h1img", "#h2img", "#srcimg", "#dstimg"];
var directlinks = ["#h1link", "#h2link", "#srclink", "#dstlink"];
var labels = [ "#h1label", "#h2label", "#srclabel", "#dstlabel"];
var speeds =  ["#speedup", "#speeddown"];
var controller = ["#controllerlabel","#controllerimg", ];
var objects = [arrowsup, arrowsdown,switches, links, hosts, controller, directlinks,labels, speeds];

var congestion_subpath = ["#h1link", "#h2link", "#link45"];


var ws = new WebSocket("ws://127.0.0.1:9090/websocket");
var mt = $("#mt");
var st = $("#st");

ws.onopen = function() {
    mt.text("Connected");
    st.text("Ready to start");
};
ws.onmessage = function (evt) {
    if (evt.data === "start"){
        startDemo();
    }
    else if (evt.data === "step1"){
        startStreaming();
    }
    else if (evt.data === "step2"){
        startController();
    }
    else if (evt.data === "step3"){
        startCongestion();
    }
    else if (evt.data === "step4"){
        readapt();
    }
    else if (evt.data === "stop"){
        end();
    }
};

function startMessage(){
    ws.send('start');
}



function hideAll(){
    $.each(objects, function(i, value ){
        $.each(value, function(j, subvalue){
            $(subvalue).hide();
        });
    });
}

function startDemo(){
    var counter = 3;
    var interval = setInterval(function() {
        st.text('Starting in ' + counter);
        st.velocity('fadeIn');
        counter--;
        if (counter == -1){
            clearInterval(interval);
            setupTopology(interval);
        }
    }, 1000);
}


function setupTopology(){
    mt.text('Step 0 - Creating emulated topology');
    st.text('');

    setTimeout(function(){
        st.velocity('fadeIn');
        st.text('Adding Switches');
        $.each(switches, function(i, val){
            var d1 = Math.floor(Math.random()*(2000-500+1)+500);
            $(val).velocity('fadeIn', {duration: d1});
        }) ;
    }, 2000);

    setTimeout(function(){
        st.velocity('fadeIn');
        st.text('Adding Links');
        $.each(links, function(i, val){
            var d1 = Math.floor(Math.random()*(2000-500+1)+500);
            $(val).velocity('fadeIn', {duration: d1});
        }) ;
        $.each(speeds, function(i, val){
            var d1 = Math.floor(Math.random()*(2000-500+1)+500);
            $(val).velocity('fadeIn', {duration: d1});
        }) ;
    }, 4000);

    setTimeout(function(){
        st.velocity('fadeIn');
        st.text('Adding Hosts');
        $.each(hosts, function(i, val){
            var d1 = Math.floor(Math.random()*(2000-500+1)+500);
            $(val).velocity('fadeIn', {duration: d1});
        }) ;
        $.each(labels, function(i, val){
            var d1 = Math.floor(Math.random()*(2000-500+1)+500);
            $(val).velocity('fadeIn', {duration: d1});
        }) ;
        $.each(directlinks, function(i, val){
            var d1 = Math.floor(Math.random()*(2000-500+1)+500);
            $(val).velocity('fadeIn', {duration: d1});
        }) ;
    }, 6000);

      setTimeout(function(){
        st.text('Configuring Single-Path Forwarding');
    }, 8000);

    setTimeout(function(){
        $("#link14").velocity(
            {fill: "#D1D0CE"},
            {duration: 500}
        );
        $("#link45").velocity(
            {fill: "#D1D0CE"},
            {duration: 500}
        );
        $("#link56").velocity(
            {fill: "#D1D0CE"},
            {duration: 500}
        );
        $("#h1link").velocity(
            {fill: "#D1D0CE"},
            {duration: 500}
        );
        $("#h2link").velocity(
            {fill: "#D1D0CE"},
            {duration: 500}
        );
    }, 8000);
    setTimeout(function(){
        $("#srclink").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );
    }, 8000);
    setTimeout(function(){
        $("#link12").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );

    }, 8500);
    setTimeout(function(){
        $("#link23").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );

    }, 9000);
    setTimeout(function(){
        $("#link36").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );

    }, 9500);
    setTimeout(function(){
        $("#dstlink").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );

    }, 10000);
}

function startStreaming(){
    mt.text('Step 1 - Single-Path Streaming');
    mt.velocity('fadeIn');
    st.html('Streaming Video <span style="font-size:0.6em">(~10 Mb/s bitrate)</span> over 7 Mb/s link');
    st.velocity('fadeIn');
    $("#srclink").velocity({fill: "#000080"}, { delay: 0, loop: true });
    $("#link12").velocity({fill: "#000080"}, { delay: 50,loop: true });
    $("#link23").velocity({fill: "#000080"}, {delay: 100, loop: true });
    $("#link36").velocity({fill: "#000080"}, {delay: 150, loop: true });
    $("#dstlink").velocity({fill: "#000080"}, {delay: 200, loop: true });
}

function startController(){
    mt.text('Step 2 - Multipath Streaming');
    mt.velocity('fadeIn');
    st.text('Starting Controller');
    st.velocity('fadeIn');
    $.each(controller, function(key, value){
        $(value).velocity('fadeIn', {duration: 1000});
    });
    setTimeout(function(){
        st.html('Using LLDP to learn topology');
        st.velocity('fadeIn');
        $.each(arrowsup, function(i, val){
            var d1 = Math.floor(Math.random()*(1000-500+1)+500 );
            $(val).velocity('fadeIn', {duration: d1, loop: 3});
        }) ;
    }, 3000);
    setTimeout(function(){
        st.html('Measuring Latency');
        st.velocity('fadeIn');
        $.each(arrowsdown, function(i, val){
            var d1 = Math.floor(Math.random()*(1000-500+1)+500 );
            $(val).velocity('fadeIn', {duration: d1, loop: 3});
        }) ;
    }, 7000);
    setTimeout(function(){
        st.html('Computing Multipath Forwarding');
        st.velocity('fadeIn');
    }, 10000);
    setTimeout(function(){
        st.html('Sending rules to the switches');
        st.velocity('fadeIn');
        $.each(arrowsdown, function(i, val){
            var d1 = Math.floor(Math.random()*(1000-500+1)+500 );
            $(val).velocity('fadeIn', {duration: d1, loop: 2});
        }) ;
        $("#srclink").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );
        $("#link14").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );
        $("#link45").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );
        $("#link56").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );
        $("#h1link").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );
        $("#h2link").velocity(
            {fill: "#2FD566"},
            {duration: 500}
        );
    }, 13000);
    setTimeout(function(){
        st.html('Multipath Streaming over an aggregated ~14 Mb/s Channel');
        $("#srclink").velocity({fill: "#000080"}, { delay: 0, loop: true });
        $("#link14").velocity({fill: "#000080"}, { delay: 50,loop: true });
        $("#link45").velocity({fill: "#000080"}, {delay: 100, loop: true });
        $("#link56").velocity({fill: "#000080"}, {delay: 150, loop: true });
    }, 15000);
}

function startCongestion(){
    mt.text('Step 3 - Sub-Path Congestion');
    mt.velocity('fadeIn');
    st.html('');
    setTimeout(function(){
        st.html('Streaming <b>20 Mb/s</b> UDP Flow from H1 to H2');
        st.velocity('fadeIn');
        $.each(congestion_subpath, function(key,val){
            $(val).velocity({fill: "#FF0000"},{duration: 200});
        });
    }, 2000);
}

function readapt(){
    mt.text('Step 4 - Readapting Forwarding Tables');
    mt.velocity('fadeIn');
    st.html('');
    setTimeout(function(){
        st.html('Measuring port usage');
        st.velocity('fadeIn');
        $.each(arrowsdown, function(i, val){
            var d1 = Math.floor(Math.random()*(1000-200+1)+200 );
            $(val).velocity('fadeIn', {duration: d1, loop: 2});
        }) ;
        $.each(arrowsup, function(i, val){
            var d1 = Math.floor(Math.random()*(1000-200+1)+200 );
            $(val).velocity('fadeIn', {duration: d1, loop: 2});
        }) ;
    }, 2000);
    setTimeout(function(){
        st.html('Recomputing Multipath Forwarding');
        st.velocity('fadeIn');
    }, 6000);
    setTimeout(function(){
        st.html('Sending rules to the switches');
        st.velocity('fadeIn');
        $.each(arrowsdown, function(i, val){
            var d1 = Math.floor(Math.random()*(1000-200+1)+200 );
            $(val).velocity('fadeIn', {duration: d1, loop: 2});
        }) ;
    }, 9000);
    setTimeout(function(){
        st.html('Singlepath Streaming');
        st.velocity('fadeIn');
        $("#link14").velocity("stop");
        $("#link56").velocity("stop");
        $("#link14").velocity(
            {fill: "#D1D0CE"},
            {duration: 500}
        );
        $("#link56").velocity(
            {fill: "#D1D0CE"},
            {duration: 500}
        );
    }, 12000);
}

function end(){
    mt.text('Stop');
    mt.velocity('fadeIn');
    st.html('End of Demo');
    st.velocity('fadeIn');
    hideAll();
}


hideAll();