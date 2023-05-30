const api_path = '/api';

function api(path, data={}, on_success=null) {
    return $.ajax(api_path + path, {
        type: 'POST',
        data: data,
        dataType: 'json',
        success: function (result) {
            if (on_success != null){
                on_success(result);
            }

        },
        error: function (xhr) {
        }
    });
}

