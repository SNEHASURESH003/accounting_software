# accounting_app/views/controls.py
from datetime import date
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin  # add PermissionRequiredMixin later if you want
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

# IMPORTANT: import from models_controls, not models
from accounting_app.models import ControlTask, ControlTaskInstance
from accounting_app.forms_controls import ControlTaskForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import ControlTask,User
from django.contrib.auth import get_user_model
from datetime import date
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.contrib.auth import get_user_model

from .models import ControlTask, ControlTaskInstance
from .forms_controls import ControlTaskForm

from datetime import date
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from django.http import Http404

from .models import ControlTask, ControlTaskInstance
from .forms_controls import ControlTaskForm

User = get_user_model()

class ControlTaskListView(LoginRequiredMixin, ListView):
    model = ControlTask
    template_name = "controls/task_list.html"
    context_object_name = "tasks"

    def get_queryset(self):
        user = self.request.user

        if getattr(user, "is_superadmin", False):
            # Superadmin sees everything
            return (
                ControlTask.objects
                .select_related("area", "owner")
                .order_by("area__name", "title")
            )

        elif user.is_superuser:
            # Superuser sees their own + their accountants
            allowed_users = [user] + list(user.created_users.all())

        else:
            # Accountant sees their own + their superuser (created_by)
            superuser = getattr(user, "created_by", None)
            allowed_users = [user]
            if superuser:
                allowed_users.append(superuser)

        return (
            ControlTask.objects
            .filter(owner__in=allowed_users)
            .select_related("area", "owner")
            .order_by("area__name", "title")
        )


class ControlTaskCreateView(LoginRequiredMixin, CreateView):
    model = ControlTask
    form_class = ControlTaskForm
    template_name = "controls/task_form.html"
    success_url = reverse_lazy("task_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user  # pass user for filtering owner choices
        return kwargs

    def form_valid(self, form):
        # Set created_by automatically
        if not form.instance.created_by:
            form.instance.created_by = self.request.user

        resp = super().form_valid(form)

        # Ensure current period instance exists
        y, m = date.today().year, date.today().month
        period_month = m if self.object.cadence in ("MONTHLY", "QUARTERLY") else None
        if self.object.active:
            ControlTaskInstance.objects.get_or_create(
                task=self.object, period_year=y, period_month=period_month
            )

        messages.success(self.request, "Control task created successfully.")
        return resp


class ControlTaskUpdateView(LoginRequiredMixin, UpdateView):
    model = ControlTask
    form_class = ControlTaskForm
    template_name = "controls/task_form.html"
    success_url = reverse_lazy("task_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        resp = super().form_valid(form)
        y, m = date.today().year, date.today().month
        period_month = m if self.object.cadence in ("MONTHLY", "QUARTERLY") else None
        if self.object.active:
            ControlTaskInstance.objects.get_or_create(
                task=self.object, period_year=y, period_month=period_month
            )
        messages.success(self.request, "Control task updated successfully.")
        return resp




class ControlTaskDeleteView(LoginRequiredMixin, DeleteView):
    model = ControlTask
    template_name = "controls/task_confirm_delete.html"
    success_url = reverse_lazy("task_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Control task deleted.")
        return super().delete(request, *args, **kwargs)
