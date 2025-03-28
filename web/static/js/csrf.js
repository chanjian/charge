/**
 * 根据cookie的name获取对应的值
 * @param name
 * @returns {null}
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

//类似于装饰器和中间件，会在每次发送ajax请求前执行
$.ajaxSetup({
    beforeSend: function (xhr, settings) {
        if (!csrfSafeMethod(settings.type)) {
            //如果ajax的发送方式不是GET,HEAD,OPTIONS,TRACE中的任意一种，则设置csrftoken的值
            xhr.setRequestHeader("X-CSRFTOKEN", getCookie('csrftoken'));
        }
    }
})
