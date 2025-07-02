document.getElementById('bmiForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const height = parseFloat(document.getElementById('height').value);
    const weight = parseFloat(document.getElementById('weight').value);

    if (height > 0 && weight > 0) {
        const bmi = (weight / ((height / 100) ** 2)).toFixed(2);
        let category = "";

        if (bmi < 18.5) category = "Underweight";
        else if (bmi < 24.9) category = "Normal";
        else if (bmi < 29.9) category = "Overweight";
        else category = "Obese";

        document.getElementById('result').innerText = `Your BMI is ${bmi} (${category})`;
    } else {
        document.getElementById('result').innerText = "Please enter valid height and weight!";
    }
});
