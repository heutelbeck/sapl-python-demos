from django import forms


class UpdatePatientData(forms.Form):
    attending_doctor = forms.CharField(label='attending doctor', max_length=50, required=False)
    room_number = forms.IntegerField(label='new room number', min_value=1, max_value=99, required=False)


class UpdatePatientDiagnose(forms.Form):
    diagnose = forms.CharField(label='new diagnose', max_length=1000, required=False)
    icd11 = forms.CharField(label='new icd', max_length=100, required=False)


class NewPatientForm(forms.Form):
    name = forms.CharField(label='name', max_length=50)
    attending_doctor = forms.CharField(label='attending doctor', max_length=50, required=False)
    room_number = forms.IntegerField(label='room number', min_value=1, max_value=99)
    diagnosis_text = forms.CharField(label='diagnose', max_length=1000)
    icd11_code = forms.CharField(label='icd', max_length=100, required=False)

