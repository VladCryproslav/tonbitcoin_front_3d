# lottery/views.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Lottery, LotteryParticipant
from .serializers import LotterySerializer, LotteryParticipantSerializer
import requests

@api_view(['GET'])
def lottery_data(request):
    """Получить данные о лотерее"""
    try:
        lottery = Lottery.objects.first()
        if not lottery:
            # Создаем лотерею если её нет
            lottery = Lottery.objects.create()
        
        serializer = LotterySerializer(lottery)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def lottery_participants(request):
    """Получить список участников лотереи"""
    try:
        participants = LotteryParticipant.objects.all().order_by('-created_at')
        serializer = LotteryParticipantSerializer(participants, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def buy_lottery_ticket(request):
    """Купить билет лотереи"""
    try:
        wallet_address = request.data.get('wallet_address')
        transaction_hash = request.data.get('transaction_hash')
        amount = request.data.get('amount')
        
        # Валидация данных
        if not all([wallet_address, transaction_hash, amount]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
        
        if amount != 0.01:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем транзакцию через TON API
        if not verify_transaction(transaction_hash, wallet_address, amount):
            return Response({'error': 'Invalid transaction'}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            # Получаем лотерею
            lottery = Lottery.objects.first()
            if not lottery:
                lottery = Lottery.objects.create()
            
            # Проверяем активность и наличие билетов
            if not lottery.is_active:
                return Response({'error': 'Lottery is not active'}, status=status.HTTP_400_BAD_REQUEST)
            
            if lottery.remaining_tickets <= 0:
                return Response({'error': 'No tickets available'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Находим или создаем участника
            participant, created = LotteryParticipant.objects.get_or_create(
                wallet_address=wallet_address,
                defaults={
                    'user': request.user,
                    'username': request.user.username or 'Anonymous',
                    'tickets_count': 1,
                    'transaction_hash': transaction_hash
                }
            )
            
            if not created:
                # Участник уже существует - увеличиваем количество билетов
                participant.tickets_count += 1
                participant.transaction_hash = transaction_hash  # Обновляем последнюю транзакцию
                participant.save()
            
            # Уменьшаем количество оставшихся билетов
            lottery.remaining_tickets -= 1
            
            # Если билеты закончились - деактивируем лотерею
            if lottery.remaining_tickets <= 0:
                lottery.is_active = False
            
            lottery.save()
            
            return Response({
                'success': True,
                'message': 'Ticket purchased successfully',
                'tickets_count': participant.tickets_count
            })
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def verify_transaction(transaction_hash, wallet_address, amount):
    """Проверяем транзакцию через TON API"""
    try:
        # Здесь должна быть логика проверки транзакции через TON API
        # Пока возвращаем True для примера
        return True
    except:
        return False

# lottery/models.py
from django.db import models
from django.contrib.auth.models import User

class Lottery(models.Model):
    total_tickets = models.IntegerField(default=150)
    remaining_tickets = models.IntegerField(default=150)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Lottery {self.id} - {self.remaining_tickets}/{self.total_tickets} tickets"

class LotteryParticipant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(max_length=100)
    wallet_address = models.CharField(max_length=100)
    tickets_count = models.IntegerField(default=1)
    transaction_hash = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['wallet_address']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} - {self.tickets_count} tickets"

# lottery/serializers.py
from rest_framework import serializers
from .models import Lottery, LotteryParticipant

class LotterySerializer(serializers.ModelSerializer):
    class Meta:
        model = Lottery
        fields = ['total_tickets', 'remaining_tickets', 'is_active']

class LotteryParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = LotteryParticipant
        fields = ['id', 'username', 'wallet_address', 'tickets_count', 'created_at']

# lottery/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('lottery/data/', views.lottery_data, name='lottery_data'),
    path('lottery/participants/', views.lottery_participants, name='lottery_participants'),
    path('lottery/buy-ticket/', views.buy_lottery_ticket, name='buy_lottery_ticket'),
]
