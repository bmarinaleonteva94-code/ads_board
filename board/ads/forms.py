from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Ad, Message


class AdForm(forms.ModelForm):
    MAX_IMAGE_SIZE = 5 * 1024 * 1024

    class Meta:
        model = Ad
        fields = ('title', 'description', 'price', 'category', 'image', 'phone', 'city')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',  
            }),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7...'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError('Цена не может быть отрицательной')
        return price

    def clean_image(self):
        image = self.cleaned_data.get('image')

        if not image:
            return image

        if image.size > self.MAX_IMAGE_SIZE:
            size_mb = image.size / 1024 / 1024
            raise forms.ValidationError(
                f'Файл слишком большой ({size_mb:.1f} МБ). '
                f'Максимальный размер — 5 МБ.'
            )

        if hasattr(image, 'content_type') and not image.content_type.startswith('image/'):
            raise forms.ValidationError('Можно загружать только изображения (JPG, PNG, GIF, WEBP).')

        return image


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'})
    )

    class Meta:
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'email':
                field.widget.attrs.setdefault('class', 'form-control')

    def clean_username(self):
        """Проверка уникальности логина (без учёта регистра)."""
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует.')
        return username

    def clean_email(self):
        """Проверка уникальности email (без учёта регистра)."""
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует.')
        return email
    

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Здравствуйте! Ещё актуально?',
            }),
        }

    def clean_text(self):
        text = self.cleaned_data['text'].strip()
        if len(text) < 2:
            raise forms.ValidationError('Сообщение слишком короткое.')
        return text