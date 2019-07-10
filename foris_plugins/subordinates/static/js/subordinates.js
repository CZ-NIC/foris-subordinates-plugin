// TODO separete reasonable part for dynamic js

Foris.initNetbootRecordsForms = () => {
    $(".record-form").submit((e) => {
        e.preventDefault();
        let form = $(e.currentTarget);
        let action = $(document.activeElement).attr("value");
        switch (action) {
            case "revoke":
                $.ajax({
                    type: "POST",
                    url: form.attr('action'),
                    data: `${form.serialize()}&action=${action}`,
                    success: (data) => {
                        if (data.result) {
                            Foris.loadNetbootList();
                            // TODO success message
                        } else {
                            // TODO error message
                        }
                    },
                });
                break;
            case "accept":
                $.ajax({
                    type: "POST",
                    url: form.attr('action'),
                    data: `${form.serialize()}&action=${action}`,
                    success: (data) => {
                        if (data.result) {
                            Foris.loadNetbootList();
                            // TODO success message
                        } else {
                            // TODO error message
                        }
                    },
                });
                form.find("button").prop('disabled', true);
                break;
        }
    });
}

Foris.addWsHanlder("netboot", (msg) => {
    switch(msg.action) {
        case "revoke":
        case "accept":
            Foris.loadNetbootList();
            break;
    }
});

// Update chart after page is rendred
$(document).ready(function() {
    Foris.initNetbootRecordsForms();
    Foris.loadNetbootList();
});
