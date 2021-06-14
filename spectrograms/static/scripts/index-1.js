var columns = 6;

$(document).ready(function() {
    $('#volcano').change(showMosaic);
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

    $('#endTime').val(endTime.format('YYYY-MM-DD HH:mm'));
    $('#startTime').val(startTime.format('YYYY-MM-DD HH:mm'));

    $.getJSON('locations')
        .done(function(data) {
            $('#volcano').empty();
            for (var i = 0; i < data.length; i++) {
                var volc = data[i]
                var opt = $('<option>').text(volc);
                $('#volcano').append(opt);
            }

            setColumns(6);
        });
});

function setColumns(cols) {
    columns = cols;

    $('#mosaic').css('grid-template-columns',
        `auto repeat(${cols}, 1fr) auto`
    );

    showMosaic();
}

function showMosaic() {
    var startTime = $('#startTime').val();
    var endTime = $('#endTime').val();

    //parse start and end times to actual times
    startTime = new Date(startTime.replace(' ', 'T'));
    endTime = new Date(endTime.replace(' ', 'T'));

    //make sure that minutes are on a 10-minute mark
    var start_minute = startTime.getMinutes() - startTime.getMinutes() % 10;
    startTime.setMinutes(start_minute);

    var endOffset = endTime.getMinutes() % 10;
    if (endOffset > 0) {
        end_minute = endTime.getMinutes() - endOffset + 10;
        endTime.setMinutes(end_minute);
    }

    var curTime = dayjs(startTime).format("HH:mm");
    var timeDiv = `<div class="dateBoundry"><span class="dateLabel">${curTime}</span></div>`;
    $('#mosaic').empty();
    var count = 0;
    while (startTime < endTime) {
        if (count % columns === 0) {
            $('#mosaic').append(timeDiv);
        }
        startTime.setTime(startTime.getTime() + (10 * 60 * 1000));
        var url = genImageUrl(startTime);
        var fullUrl = genImageUrl(startTime, false);
        var img = `<a href="${fullUrl}"><img src="${url}"  class="mosaicImg"></a>`
        $('#mosaic').append(img);
        count += 1;
        if (count % columns === 0) {
            curTime = dayjs(startTime).format("HH:mm");
            timeDiv = `<div class="dateBoundry"><span class="dateLabel">${curTime}</span></div>`;
            $('#mosaic').append(timeDiv);
        }
    }
}

function genImageUrl(time, small) {
    //default to small image URL
    if (typeof(small) == "undefined") {
        small = true
    }

    var volcano = $('#volcano').val();
    var year = time.getFullYear();
    var month = time.getMonth() + 1; //actual month, not zero based
    var day = time.getDate()
    var hour = time.getHours();
    var minute = time.getMinutes();

    var url = `static/plots/${volcano}/${year}/${month}/${day}/`;

    if (small === true) {
        url += 'small_'
    }

    //format for two-digit values
    month = month.toLocaleString('en-US', {
        minimumIntegerDigits: 2,
        useGrouping: false
    });

    day = day.toLocaleString('en-US', {
        minimumIntegerDigits: 2,
        useGrouping: false
    });

    hour = hour.toLocaleString('en-US', {
        minimumIntegerDigits: 2,
        useGrouping: false
    });

    minute = minute.toLocaleString('en-US', {
        minimumIntegerDigits: 2,
        useGrouping: false
    });

    url += `${year}${month}${day}T${hour}${minute}00.png`;

    return url;
}