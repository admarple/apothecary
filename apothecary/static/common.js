function validateForm(formName, required) {
    var invalid = [];
    required.forEach(function(fieldName) {
        var x = document.forms[formName][fieldName].value;
        if (x == null || x == "") {
            invalid.push(fieldName);
        }
    });
    if (invalid.length > 0) {
        alert("Required fields are empty: " + invalid.join(', '));
        return false;
    }
}
