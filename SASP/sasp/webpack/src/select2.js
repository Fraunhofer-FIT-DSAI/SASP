// Select2
import 'select2';
// Select2 CSS
import 'select2/dist/css/select2.css';
// Select2 Bootstrap Theme CSS
import 'select2-bootstrap-5-theme/dist/select2-bootstrap-5-theme.css';

let $ = jQuery;

$(function() {
    $('.select2').select2({
        theme: 'bootstrap-5',
        width: '100%',
        minimumResultsForSearch: 10,
        allowClear: true,
    });
    $('.select2-tag').select2({
        theme: 'bootstrap-5',
        width: '100%',
        allowClear: true,
        tags: true,
        placeholder: 'Select or type tags',
    });
    $('.select2-multiple').select2({
        theme: 'bootstrap-5',
        width: '100%',
        minimumResultsForSearch: 10,
        allowClear: true,
    });
    $('.select2-tags').select2({
        theme: 'bootstrap-5',
        width: '100%',
        tags: true,
        tokenSeparators: [','],
    });
});