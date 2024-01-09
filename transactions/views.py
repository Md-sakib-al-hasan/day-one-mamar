from django.shortcuts import render
from .import models
from . import forms
from accounts.models import UserBankAccount
from django.core.exceptions import ValidationError
# Create your views here.
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, ListView
from transactions.constants import DEPOSIT, WITHDRAWAL,LOAN, LOAN_PAID
from datetime import datetime
from django.db.models import Sum
from django.contrib.auth.views import PasswordChangeView
from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
)
from transactions.models import Transaction
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_transaction_email(user,amount,subject,template):
        message = render_to_string(template,{
            'user': user,
            'amount': amount,
        })
        send_email = EmailMultiAlternatives(subject, '',to = [user.email])
        send_email.attach_alternative(message,"text/html")
        send_email.send()



class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transactions/transactin_report.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'title': self.title
        })

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        # if not account.initial_deposit_date:
        #     now = timezone.now()
        #     account.initial_deposit_date = now
        account.balance += amount # amount = 200, tar ager balance = 0 taka new balance = 0+200 = 200
        account.save(
            update_fields=[
                'balance'
            ]
        )

        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )

        return super().form_valid(form)


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        print("----------------------------")
        craft  =models.Brank_Craft.objects.get(id=1).brank_craft
        print("----------------------------")
        if craft == False:
            self.request.user.account.balance -= form.cleaned_data.get('amount')
            # balance = 300
            # amount = 5000
            self.request.user.account.save(update_fields=['balance'])

            messages.success(
                self.request,
                f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
            )
        else:
            messages.success(self.request,'This Brank is Brank Craft')

        return super().form_valid(form)

class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )

        return super().form_valid(form)
    
class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transactions/transaction_form.html'
    model = Transaction
    balance = 0 # filter korar pore ba age amar total balance ke show korbe
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() # unique queryset hote hobe
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context
    
        
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('transactions:loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )

        return redirect('loan_list')


class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'transactions/loan_request.html'
    context_object_name = 'loans' 
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        print(queryset)
        return queryset
    


class transfersView(CreateView):
    template_name = 'transactions/transfer.html'
    temp = 'transfer'
    model = models.Transfer_another_account
    form_class= forms.TransferRequestForm

    def form_valid(self, form):
        data = UserBankAccount.objects.filter(account_no = form.cleaned_data.get('Account_NO'))
        if data.exists():
            
            user_account = UserBankAccount.objects.get(account_no=form.cleaned_data.get('Account_NO'))
            balance = user_account.balance
            if balance > form.cleaned_data.get('amount'):
                send_transaction_email(self.request.user,form.cleaned_data.get('amount'),"You are Transfer money",'transactions/send_mail.html')
                send_transaction_email(user_account.user,form.cleaned_data.get('amount'),"you are received money",'transactions/send_mail.html')
                messages.error(self.request,f'Your money transfer has already been successfull')
                user_account.balance += form.cleaned_data.get('amount')
                self.request.user.account.balance -= form.cleaned_data.get('amount')
                print(self.request.user.account.balance)
                self.request.user.account.save()
                user_account.save()
                
            else:
                 messages.warning(self.request,f'Your money transfer has not transferred')
        else:
             messages.warning(self.request,f'Not found Account ')
        return super().form_valid(form)
    success_url = reverse_lazy(temp)

class ChangePassword(PasswordChangeView):
    template_name = 'transactions/transfer.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):

        message = render_to_string('transactions/password_change.html',{
            'user': self.request.user
        })
        send_email = EmailMultiAlternatives("password change successfully", '',to = [self.request.user.email])
        send_email.attach_alternative(message,"text/html")
        send_email.send()

        return super().form_valid(form)