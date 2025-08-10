from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView
from .models import Profile
from .forms import ProfileForm


class ProfileListView(ListView):
    model = Profile
    template_name = 'profiles/list.html'
    context_object_name = 'profiles'


class ProfileCreateView(CreateView):
    model = Profile
    form_class = ProfileForm
    template_name = 'profiles/add.html'
    success_url = reverse_lazy('profiles:list')

# Create your views here.
