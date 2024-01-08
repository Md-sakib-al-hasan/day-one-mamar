from django.shortcuts import render
from django.views.generic import TemplateView
from django.views.generic import CreateView, ListView
# Create your views here.

class HomeView(TemplateView):
    template_name = 'index.html'


