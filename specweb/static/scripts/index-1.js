//some global variables for state storage
var columns = 6;
var volcanoes = null;

$(document).ready(function() {
    $('#volcano').change(changeVolcano);
    $('.volcNav').click(navVolcano);
    $('.timeNav').click(navTime);
    $('.dateTime').change(startChanged);
    $('#numHours').change(showMosaic);
    $('#hoursAgo').change(updateStart);
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
            volcanoes = data;
            $('#volcano').empty();
            for (var i = 0; i < data.length; i++) {
                var volc = data[i]
                var opt = $('<option>').text(volc);
                $('#volcano').append(opt);
            }

            setColumns(6);
        });
});

function toggleTimeMode() {
    $('.toggleButton.time.active').removeClass('active');
    $(this).addClass('active');
    var target = $(this).data('target');
    $('.timeOption').hide();
    $('#' + target).css('display', 'inline');
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
    var curIdx = volcanoes.indexOf($('#volcano').val());
    var prevIdx = curIdx === 0 ? volcanoes.length - 1 : curIdx - 1;
    var nextIdx = curIdx === volcanoes.length - 1 ? 0 : curIdx + 1;
    $('#prevVolc').html("&#9650; " + volcanoes[prevIdx]);
    $('#nextVolc').html(volcanoes[nextIdx] + " &#9660;");
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
    while (startTime < endTime) {
        if (count % columns === 0) {
            $('#mosaic').append(timeDiv);
        }
        startTime = startTime.add(10 * 60 * 1000); //add 10 minutes
        var url = genImageUrl(startTime);
        var fullUrl = genImageUrl(startTime, false);
        var img = `<a href="${fullUrl}"><img src="${url}"  class="mosaicImg"></a>`
        $('#mosaic').append(img);
        count += 1;
        if (count % columns === 0) {
            curTime = startTime.format("HH:mm");
            timeDiv = `<div class="dateBoundry"><span class="dateLabel">${curTime}</span></div>`;
            $('#mosaic').append(timeDiv);
        }
    }
}

function genImageUrl(time, small) {
    //time should be a dayjs object

    //default to small image URL
    if (typeof(small) == "undefined") {
        small = true
    }

    var volcano = $('#volcano').val();
    var year = time.year();
    var month = time.month() + 1; //actual month, not zero based
    var day = time.date()

    var url = `static/plots/${volcano}/${year}/${month}/${day}/`;

    if (small === true) {
        url += 'small_'
    }

    url += time.format("YYYYMMDDTHHmm00.png")

    return url;
}