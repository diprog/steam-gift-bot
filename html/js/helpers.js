const api_path = '/api';

function api(path, data = {}, on_success = null) {
    return $.ajax(api_path + path, {
        type: 'POST',
        data: data,
        dataType: 'json',
        success: function (result) {
            if (on_success != null) {
                on_success(result);
            }

        },
        error: function (xhr) {
        }
    });
}

function setThemeMode() {
    // Проверяем, является ли тема браузера тёмной
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-bs-theme', 'dark')
    } else {
        document.documentElement.setAttribute('data-bs-theme', 'light')
    }
}

function fadeIn(element, done = () => {
}) {
    element.hide();
    element.removeClass('d-none');
    element.fadeIn(100, done);
}

function fadeOut(element, done = () => {
}) {
    element.fadeOut(100, () => {
        element.hide();
        element.addClass('d-none');
        done();
    });
}