$(function () {
    bindDeleteEvent();
    bindConfirmDeleteEvent();
});

function bindDeleteEvent() {
    $(".btn-delete").click(function () {
        $("#deleteError").empty();

        $("#deleteModal").modal('show');
        var cid = $(this).attr('cid');
        DELETE_ID = cid;
    });

    $("#btnCancelDelete").click(function () {
        $("#deleteModal").modal('hide');
    });
}

function bindConfirmDeleteEvent() {
    $("#btnConfirmDelete").click(function () {

        //ajax发送请求  /xxx/xxx/xx?cid=123
        $.ajax({
            url: DELETE_URL,
            type: "GET",
            data: {cid: DELETE_ID},
            dataType: "JSON",
            success: function (res) {
                if (res.status) {
                    // 删除成功
                    // 方式一：页面的刷新
                    // location.reload();

                    // 方式二：找到当前数据行，删除
                    $("tr[row-id='" + DELETE_ID + "']").remove();
                    $("#deleteModal").modal('hide');
                } else {
                    // 删除失败
                    $("#deleteError").text(res.detail);
                }
            }
        })


    });
}
