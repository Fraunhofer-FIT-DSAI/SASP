const CONTEXT = JSON.parse(document.getElementById('js-context').textContent);

// Jank we used until now
{/* <script>
$(document).ready(function() {
    $("#{{row.id}}").click(function() {
        window.location = "{{row.href}}";
    });
    $("#{{row.id}}").css('cursor', 'pointer');
    $("#{{row.id}}").hover(function() {
        $(this).css('background-color', '#f5f5f5');
    }, function() {
        $(this).css('background-color', '');
    });
});
</script> */}

function make_table_rows_clickable(table_id) {
    // Find table by id, iterate over rows, find first a with href, assign click function to row
    // clear href from a
    // set cursor to pointer
    let table = $('#' + table_id);
    if (table.length == 0) {
        console.log("make_table_rows_clickable: Could not find table: " + table_id);
        return;
    }
    table.find('tr').each(function() {
        let row = $(this);
        let a_tag = row.find('a');
        let href = a_tag.attr('href');
        if (href != null) {
            row.click(function() {
                window.location = href;
            });
            row.css('cursor', 'pointer');
            // Just add table-hover to the table instead, no need for js
            // row.hover(function() {
            //     $(this).css('background-color', '#f5f5f5');
            // }, function() {
            //     $(this).css('background-color', '');
            // });
        }
    });
}

if (CONTEXT == null || CONTEXT.target_tables == null) {
    console.log("make_table_rows_clickable: No context found.");
}
else if ($ == null) {
    console.log("make_table_rows_clickable: jQuery not found.");
}
else {
    // Hook function make_table_rows_clickable to all ids in CONTEXT.target_tables.
    for (let id of CONTEXT.target_tables) {
        console.log("Searching for table: " + id);
        make_table_rows_clickable(id);
    }
}