from django import forms


class UpdatePatientData(forms.Form):
    attenting_doctor = forms.CharField(label='attenting doctor', max_length=50, required=False)
    room_number = forms.IntegerField(label='new room number', min_value=1, max_value=99, required=False)


class UpdatePatientDiagnose(forms.Form):
    diagnose = forms.CharField(label='new diagnose', max_length=1000, required=False)
    icd11 = forms.CharField(label='new icd', max_length=100, required=False)


class NewPatientForm(forms.Form):
    name = forms.CharField(label='name', max_length=50)
    attendingDoctor = forms.CharField(label='attenting doctor', max_length=50, required=False)
    roomNumber = forms.IntegerField(label='room number', min_value=1, max_value=99)
    diagnosisText = forms.CharField(label='diagnose', max_length=1000)
    icd11Code = forms.CharField(label='icd', max_length=100, required=False)

