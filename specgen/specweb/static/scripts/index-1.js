//some global variables for state storage
var columns = 6;
var volcanoes = null;
var sitesByVolcano = null;

$(document).ready(function() {
    $(document).on('click', '.mosaicSegment', getFullImage);
    $('#settingsToggle').click(toggleSettings);
    $('#volcano').change(changeVolcano);
    $('.volcNav').click(navVolcano);
    $('.timeNav').click(navTime);
    $('.dateTime').change(startChanged);
    $('#numHours').change(showMosaic);
    $('#hoursAgo').change(updateStart);
    $('#minsPerRow').change(function() {
        setColumns(Number(this.value) / 10);
    });

    $('.toggleButton.time').click(toggleTimeMode);

    $('.dateTime').datetimepicker({
        format: 'Y-m-d H:i',
        mask: true,
        step: 10
    });

    dayjs.extend(window.dayjs_plugin_utc)

    var cur_time = dayjs.utc();
    var min_offset = cur_time.minute() % 10;
    var endTime = cur_time.minute(cur_time.minute() - min_offset).second(0).millisecond(0);
    var startTime = endTime.subtract(2, 'hours');

    $('#startTime').val(startTime.format('YYYY-MM-DD HH:mm'));

    $.getJSON('locations')
        .done(function(data) {
            volcanoes = data['locations'];
            sitesByVolcano = data['loc_stations'];
            $('#volcano').empty();
            for (var i = 0; i < volcanoes.length; i++) {
                var volc = volcanoes[i]
                var opt = $('<option>').text(volc);
                $('#volcano').append(opt);
            }

            setColumns(6);
        });

    $('#volcano').focus();
});

function toggleTimeMode() {
    $('.toggleButton.time.active').removeClass('active');
    $(this).addClass('active');
    var target = $(this).data('target');
    $('.timeOption').hide();
    $('#' + target).css('display', 'inline');
}

function toggleSettings() {
    $('#settings').toggle();
    if ($('#settings').is(':visible')) {
        $('#main').css('grid-template-columns', 'auto 1fr');
    } else {
        $('#main').css('grid-template-columns', '1fr');
    }

}

function startChanged() {
    var offset = dayjs.utc() - dayjs.utc($('#startTime').val());
    offset = Math.round(offset / (1000 * 60 * 60));
    $('#hoursAgo').val(offset);
    showMosaic();
}

function updateStart() {
    var hourDiff = Number($('#hoursAgo').val());
    var startTime = dayjs.utc().subtract(hourDiff, 'hours');
    var minuteOffset = startTime.minute() % 10
    startTime = startTime.subtract(minuteOffset, 'minutes');
    $('#startTime').val(startTime.format('YYYY-MM-DD HH:mm'));
    showMosaic();
}

function setColumns(cols) {
    columns = cols;

    $('#mosaic').css('grid-template-columns',
        `auto repeat(${cols}, 1fr) auto`
    );

    changeVolcano();
}

function navTime() {
    var timediff = Number($('#numHours').val()) * 60 * 60 * 1000; //miliseconds
    var startTime = dayjs($('#startTime').val());
    if ($(this).data('dir') === "back") {
        var newTime = startTime.subtract(timediff);
    } else {
        var newTime = startTime.add(timediff);
    }
    $('#startTime').val(newTime.format('YYYY-MM-DD HH:mm'));
    startChanged();
    showMosaic();
}

function navVolcano() {
    var dir = Number($(this).data('dir'));
    var curIdx = volcanoes.indexOf($('#volcano').val());
    var destIdx = curIdx + dir;
    if (destIdx < 0) {
        destIdx = volcanoes.length + destIdx; //actually subtraction, since < 0
    }
    if (destIdx >= volcanoes.length) {
        destIdx = 0;
    }
    $('#volcano').val(volcanoes[destIdx]);
    changeVolcano();
}

function changeVolcano() {
    var volcano = $('#volcano').val();
    var volc_stations = sitesByVolcano[volcano];
    volc_stations.sort(function(a, b) {
        return a[1] - b[1];
    })

    var curIdx = volcanoes.indexOf(volcano);
    var prevIdx = curIdx === 0 ? volcanoes.length - 1 : curIdx - 1;
    var nextIdx = curIdx === volcanoes.length - 1 ? 0 : curIdx + 1;
    $('#prevVolc').html("&#9650; " + volcanoes[prevIdx]);
    $('#nextVolc').html(volcanoes[nextIdx] + " &#9660;");

    $('#stationSelect').empty();
    for (var i = 0; i < volc_stations.length; i++) {
        var sta = volc_stations[i];
        var name = sta[0];
        var dist = Math.round(sta[1] * 100) / 100;
        var disp = `${name} (${dist}km)`
        var html = `<li class="stationOption"><input id="station_${name}" type="checkbox" data-station=${name} />`
        html += `${disp}</li>`
        $('#stationSelect').append(html);
        $(`#station_${name}`)[0].checked = true;
    }

    showMosaic();
}

function showMosaic() {
    var startTime = dayjs($('#startTime').val());
    //make sure that minutes are on a 10-minute mark
    var start_minute = startTime.minute() - startTime.minute() % 10;
    startTime = startTime.minute(start_minute);

    var period = $('#numHours').val() * 60 * 60 * 1000 //miliseconds
    var endTime = startTime.add(period);

    var curTime = startTime.format("HH:mm");
    var timeDiv = `<div class="dateBoundry"><span class="dateLabel">${curTime}</span></div>`;
    $('#mosaic').empty();
    var count = 0;
    var stations = sitesByVolcano[$('#volcano').val()];
    stations.sort(function(a, b) {
        if (a[1] < b[1]) return -1;
        if (a[1] > b[1]) return 1;
        return 0;
    });

    while (startTime < endTime) {
        if (count % columns === 0) {
            var startDiv = $('<div class=rowStart>');
            var siteDiv = $('<div class=siteDiv>');
            for (var i = 0; i < stations.length; i++) {
                var site = stations[i][0];
                siteDiv.append(`<span class=siteLabel>${site}</span>`);
            }
            startDiv.append(timeDiv);
            startDiv.append(siteDiv);
            $('#mosaic').append(startDiv);
        }
        startTime = startTime.add(10 * 60 * 1000); //add 10 minutes
        var imgDiv = $('<div class=mosaicSegment>');
        imgDiv.data('time', startTime);
        imgDiv.data('stations', stations);
        imgDiv.data('volcano', $('#volcano').val());

        $('#mosaic').append(imgDiv);
        for (var i = 0; i < stations.length; i++) {
            var sta = stations[i][0];
            var url = genImageUrl(startTime, sta);
            var img = `<img src="${url}"  class="mosaicImg" onerror="mosaicImgErr(this)">`;
            imgDiv.append(img);
        }

        count += 1;
        if (count % columns === 0) {
            curTime = startTime.format("HH:mm");
            timeDiv = `<div class="dateBoundry"><span class="dateLabel">${curTime}</span></div>`;
            $('#mosaic').append(timeDiv);
        }
    }
}

function mosaicImgErr(img) {
    $(img).replaceWith('<div class=mosaicImg>No Data</div>');
}

function genImageUrl(time, station) {
    //time should be a dayjs object
    var year = time.year();
    var month = time.month() + 1; //actual month, not zero based
    var day = time.date()

    var url = `static/plots/${station}/${year}/${month}/${day}/`;

    url += 'small_';

    url += time.format("YYYYMMDDTHHmm00.png")

    return url;
}

function getFullImage() {
    var time = $(this).data('time').format('YYYY-MM-DDTHH:mm:ss');
    var req_stations = []
    var disp_stations = $(this).data('stations');
    for (var i = 0; i < disp_stations.length; i++) {
        req_stations.push(disp_stations[i][0]);
    }
    var req_stations = JSON.stringify(req_stations);
    var volcano = $(this).data('volcano');

    args = {
        time: time,
        stations: req_stations,
        volcano: volcano
    }

    var str = [];
    for (var p in args)
        if (args.hasOwnProperty(p)) {
            str.push(encodeURIComponent(p) + "=" + encodeURIComponent(args[p]));
        }
    var query = str.join("&");
    var url = `fullImage?${query}`;
    window.open(url);
}