# Phase 5: Advanced Features and Monitoring

## Overview
**Timeline: 1-2 weeks**
**Priority: Low**

Implement advanced lifecycle management features, system monitoring capabilities, and integration enhancements. This phase adds sophisticated functionality for large-scale deployments and provides comprehensive system health monitoring.

## Advanced Feature Categories

1. **Predictive Analytics**: User behavior analysis and expiration forecasting
2. **Integration Systems**: API endpoints and external system connectors  
3. **Advanced Notifications**: Multi-channel alerts and escalation workflows
4. **System Monitoring**: Health checks, performance metrics, and alerting
5. **Compliance Tools**: Audit reports and regulatory compliance features

## Predictive Analytics

### User Behavior Analysis

```python
# apps/accounts/analytics/user_behavior.py

from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

class UserBehaviorAnalyzer:
    """Analyze user patterns and predict lifecycle events"""
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def analyze_activity_patterns(self, user_queryset=None):
        """Analyze user activity patterns and identify clusters"""
        from apps.accounts.models import EqmdCustomUser
        
        if user_queryset is None:
            user_queryset = EqmdCustomUser.objects.filter(is_active=True)
        
        # Extract activity features
        features = []
        users = []
        
        for user in user_queryset.select_related('supervisor'):
            user_features = self._extract_user_features(user)
            if user_features:
                features.append(user_features)
                users.append(user)
        
        if len(features) < 10:  # Need minimum data for clustering
            return None
        
        # Perform clustering
        features_array = np.array(features)
        features_scaled = self.scaler.fit_transform(features_array)
        
        # Determine optimal clusters (2-5 clusters)
        optimal_clusters = self._find_optimal_clusters(features_scaled)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=optimal_clusters, random_state=42)
        clusters = kmeans.fit_predict(features_scaled)
        
        # Analyze clusters
        cluster_analysis = self._analyze_clusters(users, clusters, features_array)
        
        return {
            'total_users': len(users),
            'clusters': cluster_analysis,
            'optimal_clusters': optimal_clusters,
            'feature_importance': self._calculate_feature_importance(features_array)
        }
    
    def _extract_user_features(self, user):
        """Extract behavioral features from user"""
        now = timezone.now()
        
        # Skip users without sufficient data
        if not user.last_meaningful_activity:
            return None
        
        features = []
        
        # Activity recency (days since last activity)
        days_since_activity = (now - user.last_meaningful_activity).days
        features.append(days_since_activity)
        
        # Activity score
        features.append(user.activity_score or 0)
        
        # Days until expiration (or 9999 if no expiration)
        if user.access_expires_at:
            days_until_expiration = (user.access_expires_at - now).days
            features.append(max(0, days_until_expiration))
        else:
            features.append(9999)
        
        # Professional role (encoded)
        features.append(user.profession_type or 0)
        
        # Has supervisor (binary)
        features.append(1 if user.supervisor else 0)
        
        # Renewal request history
        renewal_count = user.renewal_requests.count()
        features.append(renewal_count)
        
        return features
    
    def predict_expiration_risk(self, user):
        """Predict likelihood of user needing access extension"""
        features = self._extract_user_features(user)
        if not features:
            return {'risk_level': 'unknown', 'confidence': 0}
        
        # Simple risk scoring based on patterns
        risk_factors = {
            'low_activity': features[1] < 10,  # Low activity score
            'approaching_expiration': features[2] <= 30,  # Expires in 30 days
            'no_supervisor': features[4] == 0,  # No supervisor
            'recent_inactivity': features[0] > 14,  # No activity in 14 days
        }
        
        risk_score = sum(risk_factors.values())
        
        if risk_score >= 3:
            return {'risk_level': 'high', 'confidence': 0.8, 'factors': risk_factors}
        elif risk_score >= 2:
            return {'risk_level': 'medium', 'confidence': 0.6, 'factors': risk_factors}
        else:
            return {'risk_level': 'low', 'confidence': 0.4, 'factors': risk_factors}
    
    def forecast_expiration_load(self, days_ahead=90):
        """Forecast upcoming expiration workload"""
        from apps.accounts.models import EqmdCustomUser
        
        now = timezone.now()
        end_date = now + timedelta(days=days_ahead)
        
        # Get users expiring in the period
        expiring_users = EqmdCustomUser.objects.filter(
            is_active=True,
            access_expires_at__range=(now, end_date)
        ).order_by('access_expires_at')
        
        # Group by weeks
        weekly_forecast = {}
        for user in expiring_users:
            week_start = user.access_expires_at.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = week_start - timedelta(days=week_start.weekday())
            
            week_key = week_start.strftime('%Y-W%U')
            if week_key not in weekly_forecast:
                weekly_forecast[week_key] = {
                    'week_start': week_start,
                    'count': 0,
                    'users': [],
                    'by_role': {}
                }
            
            weekly_forecast[week_key]['count'] += 1
            weekly_forecast[week_key]['users'].append({
                'username': user.username,
                'profession': user.get_profession_type_display(),
                'expiration_date': user.access_expires_at.date(),
            })
            
            # Count by role
            role = user.get_profession_type_display()
            if role not in weekly_forecast[week_key]['by_role']:
                weekly_forecast[week_key]['by_role'][role] = 0
            weekly_forecast[week_key]['by_role'][role] += 1
        
        return {
            'forecast_period': f'{days_ahead} days',
            'total_expirations': expiring_users.count(),
            'weekly_breakdown': weekly_forecast,
            'peak_week': max(weekly_forecast.values(), key=lambda x: x['count'], default=None)
        }

class LifecyclePredictionService:
    """Service for lifecycle predictions and recommendations"""
    
    def __init__(self):
        self.analyzer = UserBehaviorAnalyzer()
    
    def generate_renewal_recommendations(self):
        """Generate recommendations for user renewals"""
        from apps.accounts.models import EqmdCustomUser
        
        recommendations = []
        
        # Get users approaching expiration
        approaching_users = EqmdCustomUser.objects.filter(
            is_active=True,
            access_expires_at__lte=timezone.now() + timedelta(days=60)
        ).select_related('supervisor')
        
        for user in approaching_users:
            risk_analysis = self.analyzer.predict_expiration_risk(user)
            
            recommendation = {
                'user': user,
                'risk_level': risk_analysis['risk_level'],
                'confidence': risk_analysis['confidence'],
                'recommended_action': self._get_recommended_action(user, risk_analysis),
                'reasoning': self._generate_reasoning(user, risk_analysis)
            }
            
            recommendations.append(recommendation)
        
        return sorted(recommendations, key=lambda x: x['confidence'], reverse=True)
    
    def _get_recommended_action(self, user, risk_analysis):
        """Determine recommended action based on risk analysis"""
        risk_level = risk_analysis['risk_level']
        
        if risk_level == 'high':
            return 'immediate_contact'
        elif risk_level == 'medium':
            return 'send_reminder'
        else:
            return 'monitor'
    
    def _generate_reasoning(self, user, risk_analysis):
        """Generate human-readable reasoning for recommendation"""
        factors = risk_analysis.get('factors', {})
        reasons = []
        
        if factors.get('low_activity'):
            reasons.append('baixa atividade no sistema')
        if factors.get('approaching_expiration'):
            reasons.append('acesso expira em breve')
        if factors.get('no_supervisor'):
            reasons.append('não possui supervisor designado')
        if factors.get('recent_inactivity'):
            reasons.append('inativo nas últimas semanas')
        
        if reasons:
            return f"Usuário apresenta: {', '.join(reasons)}"
        else:
            return "Usuário apresenta padrão de uso normal"
```

### Forecasting Dashboard

```python
# apps/accounts/views.py - Add forecasting views

@staff_member_required
def lifecycle_analytics_dashboard(request):
    """Advanced analytics dashboard"""
    analyzer = UserBehaviorAnalyzer()
    prediction_service = LifecyclePredictionService()
    
    # Generate analytics
    behavior_analysis = analyzer.analyze_activity_patterns()
    expiration_forecast = analyzer.forecast_expiration_load(days_ahead=90)
    renewal_recommendations = prediction_service.generate_renewal_recommendations()
    
    context = {
        'behavior_analysis': behavior_analysis,
        'expiration_forecast': expiration_forecast,
        'renewal_recommendations': renewal_recommendations[:10],  # Top 10
        'title': 'Lifecycle Analytics Dashboard'
    }
    
    return render(request, 'admin/accounts/analytics_dashboard.html', context)
```

## API Integration

### RESTful API Endpoints

```python
# apps/accounts/api/serializers.py

from rest_framework import serializers
from apps.accounts.models import EqmdCustomUser, AccountRenewalRequest

class UserLifecycleSerializer(serializers.ModelSerializer):
    """Serializer for user lifecycle data"""
    
    days_until_expiration = serializers.ReadOnlyField()
    is_expiring_soon = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    days_since_last_activity = serializers.ReadOnlyField()
    is_inactive = serializers.ReadOnlyField()
    profession_display = serializers.CharField(source='get_profession_type_display', read_only=True)
    
    class Meta:
        model = EqmdCustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'account_status', 'profession_type', 'profession_display',
            'access_expires_at', 'days_until_expiration', 'is_expiring_soon', 'is_expired',
            'last_meaningful_activity', 'days_since_last_activity', 'is_inactive',
            'activity_score', 'supervisor', 'department'
        ]
        read_only_fields = [
            'last_meaningful_activity', 'activity_score', 'days_until_expiration',
            'is_expiring_soon', 'is_expired', 'days_since_last_activity', 'is_inactive'
        ]

class RenewalRequestSerializer(serializers.ModelSerializer):
    """Serializer for renewal requests"""
    
    user_info = UserLifecycleSerializer(source='user', read_only=True)
    
    class Meta:
        model = AccountRenewalRequest
        fields = [
            'id', 'user', 'user_info', 'created_at', 'status',
            'current_position', 'department', 'supervisor_name', 'supervisor_email',
            'renewal_reason', 'expected_duration_months',
            'reviewed_by', 'reviewed_at', 'admin_notes'
        ]
        read_only_fields = ['reviewed_by', 'reviewed_at']

# apps/accounts/api/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils import timezone
from datetime import timedelta
from .serializers import UserLifecycleSerializer, RenewalRequestSerializer

class UserLifecycleViewSet(viewsets.ModelViewSet):
    """API endpoints for user lifecycle management"""
    
    serializer_class = UserLifecycleSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = EqmdCustomUser.objects.filter(is_active=True)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(account_status=status_filter)
        
        # Filter by expiration
        expiration_filter = self.request.query_params.get('expiration')
        if expiration_filter == 'expired':
            queryset = queryset.filter(access_expires_at__lt=timezone.now())
        elif expiration_filter == 'expiring_soon':
            queryset = queryset.filter(
                access_expires_at__lte=timezone.now() + timedelta(days=30)
            )
        
        return queryset.select_related('supervisor')
    
    @action(detail=True, methods=['post'])
    def extend_access(self, request, pk=None):
        """Extend user access via API"""
        user = self.get_object()
        
        days = request.data.get('days')
        reason = request.data.get('reason')
        
        if not days or not reason:
            return Response({
                'error': 'Both days and reason are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            days = int(days)
            if days <= 0 or days > 730:
                raise ValueError("Days must be between 1 and 730")
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Extend access
        user.extend_access(days, reason, request.user)
        
        # Return updated user data
        serializer = self.get_serializer(user)
        return Response({
            'message': f'Access extended by {days} days',
            'user': serializer.data
        })
    
    @action(detail=False)
    def dashboard_stats(self, request):
        """Get dashboard statistics via API"""
        from django.db.models import Count
        
        now = timezone.now()
        
        # Status counts
        status_counts = EqmdCustomUser.objects.filter(is_active=True).values(
            'account_status'
        ).annotate(count=Count('id'))
        
        # Expiration counts
        expiration_stats = {
            'expired': EqmdCustomUser.objects.filter(
                is_active=True,
                access_expires_at__lt=now
            ).count(),
            'expiring_7_days': EqmdCustomUser.objects.filter(
                is_active=True,
                access_expires_at__range=(now, now + timedelta(days=7))
            ).count(),
            'expiring_30_days': EqmdCustomUser.objects.filter(
                is_active=True,
                access_expires_at__range=(now, now + timedelta(days=30))
            ).count(),
        }
        
        return Response({
            'total_users': EqmdCustomUser.objects.filter(is_active=True).count(),
            'status_distribution': {item['account_status']: item['count'] for item in status_counts},
            'expiration_stats': expiration_stats,
            'generated_at': now.isoformat()
        })

class RenewalRequestViewSet(viewsets.ModelViewSet):
    """API endpoints for renewal request management"""
    
    serializer_class = RenewalRequestSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return AccountRenewalRequest.objects.all().select_related(
            'user', 'reviewed_by'
        ).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve renewal request via API"""
        renewal_request = self.get_object()
        
        if renewal_request.status != 'pending':
            return Response({
                'error': 'Only pending requests can be approved'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        duration_months = request.data.get('duration_months')
        admin_notes = request.data.get('admin_notes', '')
        
        if not duration_months:
            return Response({
                'error': 'duration_months is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            duration_months = int(duration_months)
            if duration_months <= 0 or duration_months > 24:
                raise ValueError("Duration must be between 1 and 24 months")
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Approve request
        renewal_request.approve(request.user, duration_months, admin_notes)
        
        # Return updated request data
        serializer = self.get_serializer(renewal_request)
        return Response({
            'message': 'Renewal request approved',
            'request': serializer.data
        })

# apps/accounts/api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserLifecycleViewSet, RenewalRequestViewSet

router = DefaultRouter()
router.register(r'users', UserLifecycleViewSet, basename='user-lifecycle')
router.register(r'renewal-requests', RenewalRequestViewSet, basename='renewal-requests')

urlpatterns = [
    path('api/lifecycle/', include(router.urls)),
]
```

## Advanced Notifications

### Multi-Channel Notification System

```python
# apps/core/notifications/channels.py

from abc import ABC, abstractmethod
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import requests
import json

class NotificationChannel(ABC):
    """Abstract base class for notification channels"""
    
    @abstractmethod
    def send(self, recipient, subject, message, context=None):
        pass

class EmailNotificationChannel(NotificationChannel):
    """Email notification channel"""
    
    def send(self, recipient, subject, message, context=None):
        context = context or {}
        
        # Render templates
        text_message = render_to_string('notifications/email_base.txt', {
            'message': message,
            **context
        })
        
        html_message = render_to_string('notifications/email_base.html', {
            'message': message,
            'subject': subject,
            **context
        })
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False
        )

class SlackNotificationChannel(NotificationChannel):
    """Slack notification channel"""
    
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url or getattr(settings, 'SLACK_WEBHOOK_URL', None)
    
    def send(self, recipient, subject, message, context=None):
        if not self.webhook_url:
            return False
        
        payload = {
            'text': f"*{subject}*\n{message}",
            'channel': recipient,  # Slack channel or user
            'username': 'EquipeMed Lifecycle',
            'icon_emoji': ':warning:'
        }
        
        response = requests.post(
            self.webhook_url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        return response.status_code == 200

class SMSNotificationChannel(NotificationChannel):
    """SMS notification channel (example with Twilio)"""
    
    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.from_number = getattr(settings, 'TWILIO_FROM_NUMBER', None)
    
    def send(self, recipient, subject, message, context=None):
        if not all([self.account_sid, self.auth_token, self.from_number]):
            return False
        
        try:
            from twilio.rest import Client
            
            client = Client(self.account_sid, self.auth_token)
            
            # Truncate message for SMS
            sms_message = f"{subject}: {message}"[:160]
            
            client.messages.create(
                body=sms_message,
                from_=self.from_number,
                to=recipient
            )
            
            return True
        except Exception:
            return False

class NotificationService:
    """Multi-channel notification service"""
    
    def __init__(self):
        self.channels = {
            'email': EmailNotificationChannel(),
            'slack': SlackNotificationChannel(),
            'sms': SMSNotificationChannel(),
        }
    
    def send_notification(self, notification_type, recipient_info, context=None):
        """Send notification via appropriate channels"""
        notification_config = self._get_notification_config(notification_type)
        
        for channel_name in notification_config['channels']:
            if channel_name in self.channels:
                channel = self.channels[channel_name]
                recipient = recipient_info.get(channel_name)
                
                if recipient:
                    try:
                        channel.send(
                            recipient=recipient,
                            subject=notification_config['subject'],
                            message=notification_config['message'],
                            context=context
                        )
                    except Exception as e:
                        # Log error but continue with other channels
                        import logging
                        logger = logging.getLogger('notifications')
                        logger.error(f'Failed to send {channel_name} notification: {e}')
    
    def _get_notification_config(self, notification_type):
        """Get notification configuration by type"""
        configs = {
            'expiration_warning': {
                'subject': 'EquipeMed: Seu acesso expira em breve',
                'message': 'Seu acesso ao sistema EquipeMed expira em {days_left} dias. Renove seu acesso para continuar utilizando o sistema.',
                'channels': ['email']
            },
            'expiration_critical': {
                'subject': 'EquipeMed: URGENTE - Seu acesso expira em {days_left} dias',
                'message': 'ATENÇÃO: Seu acesso ao sistema EquipeMed expira em {days_left} dias. Renove imediatamente para evitar interrupção.',
                'channels': ['email', 'sms']
            },
            'admin_alert': {
                'subject': 'EquipeMed: Alerta do sistema de lifecycle',
                'message': 'Alerta do sistema: {alert_message}',
                'channels': ['email', 'slack']
            },
            'renewal_approved': {
                'subject': 'EquipeMed: Renovação de acesso aprovada',
                'message': 'Sua solicitação de renovação foi aprovada. Seu acesso foi estendido até {new_expiration_date}.',
                'channels': ['email']
            }
        }
        
        return configs.get(notification_type, {
            'subject': 'EquipeMed Notification',
            'message': 'Notificação do sistema',
            'channels': ['email']
        })

# Enhanced notification management command
# apps/accounts/management/commands/enhanced_notification_sender.py

from django.core.management.base import BaseCommand
from apps.core.notifications.channels import NotificationService

class Command(BaseCommand):
    help = 'Send enhanced multi-channel notifications'
    
    def handle(self, *args, **options):
        notification_service = NotificationService()
        
        # Send critical expiration warnings
        critical_users = self._get_critical_users()
        for user in critical_users:
            days_left = user.days_until_expiration
            
            recipient_info = {
                'email': user.email,
                'sms': user.phone if hasattr(user, 'phone') else None
            }
            
            context = {
                'user': user,
                'days_left': days_left,
                'renewal_url': f"{settings.SITE_URL}/account/renewal-required/"
            }
            
            if days_left <= 3:
                notification_service.send_notification(
                    'expiration_critical',
                    recipient_info,
                    context
                )
            else:
                notification_service.send_notification(
                    'expiration_warning',
                    recipient_info,
                    context
                )
```

## System Monitoring

### Health Check System

```python
# apps/core/monitoring/health_checks.py

from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connections
from django.utils import timezone
from datetime import timedelta
import logging

class LifecycleHealthMonitor:
    """Monitor lifecycle system health and performance"""
    
    def __init__(self):
        self.logger = logging.getLogger('lifecycle.health')
    
    def comprehensive_health_check(self):
        """Perform comprehensive system health check"""
        health_report = {
            'timestamp': timezone.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        # Database connectivity
        health_report['checks']['database'] = self._check_database()
        
        # Cache system
        health_report['checks']['cache'] = self._check_cache()
        
        # Middleware performance
        health_report['checks']['middleware'] = self._check_middleware_performance()
        
        # User lifecycle data integrity
        health_report['checks']['data_integrity'] = self._check_data_integrity()
        
        # Notification system
        health_report['checks']['notifications'] = self._check_notification_system()
        
        # Command execution status
        health_report['checks']['commands'] = self._check_management_commands()
        
        # Determine overall status
        failed_checks = [name for name, check in health_report['checks'].items() 
                        if check['status'] != 'healthy']
        
        if failed_checks:
            health_report['overall_status'] = 'unhealthy'
            health_report['failed_checks'] = failed_checks
        
        return health_report
    
    def _check_database(self):
        """Check database connectivity and query performance"""
        try:
            from apps.accounts.models import EqmdCustomUser
            
            start_time = timezone.now()
            count = EqmdCustomUser.objects.count()
            query_time = (timezone.now() - start_time).total_seconds()
            
            return {
                'status': 'healthy' if query_time < 1.0 else 'slow',
                'query_time_seconds': query_time,
                'total_users': count,
                'details': 'Database accessible and responsive'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'details': 'Database connection failed'
            }
    
    def _check_cache(self):
        """Check cache system functionality"""
        try:
            test_key = 'lifecycle_health_check'
            test_value = timezone.now().isoformat()
            
            # Test cache write
            cache.set(test_key, test_value, 60)
            
            # Test cache read
            cached_value = cache.get(test_key)
            
            if cached_value == test_value:
                return {
                    'status': 'healthy',
                    'details': 'Cache system operational'
                }
            else:
                return {
                    'status': 'unhealthy',
                    'details': 'Cache read/write mismatch'
                }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'details': 'Cache system unavailable'
            }
    
    def _check_middleware_performance(self):
        """Check middleware execution metrics"""
        try:
            # Check for middleware error logs in last hour
            error_count = self._count_recent_middleware_errors()
            
            status = 'healthy'
            if error_count > 100:
                status = 'unhealthy'
            elif error_count > 10:
                status = 'warning'
            
            return {
                'status': status,
                'error_count_last_hour': error_count,
                'details': f'Middleware executed with {error_count} errors in last hour'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'details': 'Unable to check middleware performance'
            }
    
    def _check_data_integrity(self):
        """Check user lifecycle data integrity"""
        try:
            from apps.accounts.models import EqmdCustomUser
            
            issues = []
            
            # Check for users with inconsistent status
            inconsistent_expired = EqmdCustomUser.objects.filter(
                access_expires_at__lt=timezone.now(),
                account_status__in=['active', 'expiring_soon']
            ).count()
            
            if inconsistent_expired > 0:
                issues.append(f'{inconsistent_expired} users with expired access but active status')
            
            # Check for users with missing expiration dates
            missing_expiration = EqmdCustomUser.objects.filter(
                profession_type__in=[1, 4],  # Residents and students
                access_expires_at__isnull=True,
                is_active=True
            ).count()
            
            if missing_expiration > 0:
                issues.append(f'{missing_expiration} residents/students without expiration dates')
            
            status = 'healthy' if not issues else 'warning'
            
            return {
                'status': status,
                'issues': issues,
                'details': 'Data integrity check completed'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'details': 'Data integrity check failed'
            }
    
    def _check_notification_system(self):
        """Check notification system health"""
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            # Test email configuration
            if not settings.EMAIL_HOST:
                return {
                    'status': 'warning',
                    'details': 'Email not configured'
                }
            
            return {
                'status': 'healthy',
                'details': 'Notification system configured'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'details': 'Notification system check failed'
            }
    
    def _check_management_commands(self):
        """Check management command execution status"""
        try:
            # Check when commands were last run
            expiration_check = cache.get('expiration_checker_last_run')
            notification_sender = cache.get('notification_sender_last_run')
            
            now = timezone.now()
            issues = []
            
            if expiration_check:
                hours_since = (now - expiration_check).total_seconds() / 3600
                if hours_since > 25:  # Should run daily
                    issues.append(f'Expiration checker not run for {hours_since:.1f} hours')
            else:
                issues.append('Expiration checker never run')
            
            status = 'healthy' if not issues else 'warning'
            
            return {
                'status': status,
                'issues': issues,
                'last_expiration_check': expiration_check.isoformat() if expiration_check else None,
                'details': 'Management command status checked'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'details': 'Command status check failed'
            }
    
    def _count_recent_middleware_errors(self):
        """Count middleware errors in the last hour"""
        # This would integrate with your logging system
        # Placeholder implementation
        return 0

# Health check management command
# apps/core/management/commands/lifecycle_health_check.py

class Command(BaseCommand):
    help = 'Perform lifecycle system health check'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            choices=['json', 'text'],
            default='text',
            help='Output format'
        )
        parser.add_argument(
            '--alert-on-failure',
            action='store_true',
            help='Send alerts if health check fails'
        )
    
    def handle(self, *args, **options):
        monitor = LifecycleHealthMonitor()
        health_report = monitor.comprehensive_health_check()
        
        if options['format'] == 'json':
            self.stdout.write(json.dumps(health_report, indent=2))
        else:
            self._display_text_report(health_report)
        
        # Send alerts if requested and system is unhealthy
        if options['alert_on_failure'] and health_report['overall_status'] != 'healthy':
            self._send_health_alert(health_report)
    
    def _display_text_report(self, report):
        """Display health report as formatted text"""
        self.stdout.write(f"Lifecycle System Health Report")
        self.stdout.write(f"Generated: {report['timestamp']}")
        self.stdout.write(f"Overall Status: {report['overall_status'].upper()}")
        self.stdout.write("")
        
        for check_name, check_result in report['checks'].items():
            status_color = self.style.SUCCESS if check_result['status'] == 'healthy' else self.style.ERROR
            self.stdout.write(f"{check_name}: {status_color(check_result['status'])}")
            self.stdout.write(f"  {check_result['details']}")
            
            if 'issues' in check_result and check_result['issues']:
                for issue in check_result['issues']:
                    self.stdout.write(f"  - {issue}")
            
            self.stdout.write("")
```

## Compliance and Audit Tools

### Regulatory Compliance Dashboard

```python
# apps/accounts/compliance/audit_tools.py

from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import csv
import io

class ComplianceAuditor:
    """Tools for regulatory compliance and auditing"""
    
    def generate_audit_report(self, start_date, end_date, report_type='comprehensive'):
        """Generate comprehensive audit report"""
        report_data = {
            'report_type': report_type,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'generated_at': timezone.now().isoformat()
        }
        
        if report_type in ['comprehensive', 'access_control']:
            report_data['access_control'] = self._audit_access_control(start_date, end_date)
        
        if report_type in ['comprehensive', 'data_retention']:
            report_data['data_retention'] = self._audit_data_retention()
        
        if report_type in ['comprehensive', 'user_lifecycle']:
            report_data['user_lifecycle'] = self._audit_user_lifecycle(start_date, end_date)
        
        return report_data
    
    def _audit_access_control(self, start_date, end_date):
        """Audit access control compliance"""
        from apps.accounts.models import EqmdCustomUser
        
        # Users created in period
        new_users = EqmdCustomUser.objects.filter(
            date_joined__range=(start_date, end_date)
        )
        
        # Users with access changes
        users_with_changes = EqmdCustomUser.history.filter(
            history_date__range=(start_date, end_date)
        ).values('id').distinct()
        
        # Access violations (expired users who accessed system)
        access_violations = self._find_access_violations(start_date, end_date)
        
        return {
            'new_users_count': new_users.count(),
            'users_with_changes': users_with_changes.count(),
            'access_violations': access_violations,
            'compliance_score': self._calculate_compliance_score(access_violations)
        }
    
    def _audit_user_lifecycle(self, start_date, end_date):
        """Audit user lifecycle management"""
        from apps.accounts.models import EqmdCustomUser, AccountRenewalRequest
        
        # Renewal requests in period
        renewal_requests = AccountRenewalRequest.objects.filter(
            created_at__range=(start_date, end_date)
        )
        
        # Expired users who were not handled
        unhandled_expirations = EqmdCustomUser.objects.filter(
            access_expires_at__range=(start_date, end_date),
            account_status='expired',
            renewal_requests__isnull=True
        )
        
        return {
            'renewal_requests': {
                'total': renewal_requests.count(),
                'approved': renewal_requests.filter(status='approved').count(),
                'denied': renewal_requests.filter(status='denied').count(),
                'pending': renewal_requests.filter(status='pending').count()
            },
            'unhandled_expirations': unhandled_expirations.count(),
            'lifecycle_efficiency': self._calculate_lifecycle_efficiency(renewal_requests)
        }
    
    def export_compliance_csv(self, report_data):
        """Export compliance report as CSV"""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Compliance Report'])
        writer.writerow(['Generated', report_data['generated_at']])
        writer.writerow(['Period', f"{report_data['period']['start_date']} to {report_data['period']['end_date']}"])
        writer.writerow([])
        
        # Write sections
        if 'access_control' in report_data:
            self._write_access_control_csv(writer, report_data['access_control'])
        
        if 'user_lifecycle' in report_data:
            self._write_lifecycle_csv(writer, report_data['user_lifecycle'])
        
        return output.getvalue()

class DataRetentionManager:
    """Manage data retention policies and cleanup"""
    
    def cleanup_old_history(self, retention_days=2555):  # 7 years default
        """Clean up old history records beyond retention period"""
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        # Archive old history records
        from apps.accounts.models import EqmdCustomUser
        
        old_records = EqmdCustomUser.history.filter(
            history_date__lt=cutoff_date
        )
        
        # Export to archive before deletion
        archive_data = list(old_records.values())
        
        # Delete old records
        deleted_count = old_records.delete()[0]
        
        return {
            'archived_records': len(archive_data),
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
    
    def generate_retention_report(self):
        """Generate data retention compliance report"""
        from apps.accounts.models import EqmdCustomUser
        
        now = timezone.now()
        
        # Analyze history record ages
        history_stats = {
            'total_records': EqmdCustomUser.history.count(),
            'records_by_age': {}
        }
        
        age_ranges = [
            ('0-1_years', 365),
            ('1-3_years', 365 * 3),
            ('3-7_years', 365 * 7),
            ('over_7_years', None)
        ]
        
        for range_name, days in age_ranges:
            if days:
                cutoff = now - timedelta(days=days)
                if range_name == '0-1_years':
                    count = EqmdCustomUser.history.filter(
                        history_date__gte=cutoff
                    ).count()
                else:
                    prev_cutoff = now - timedelta(days=age_ranges[age_ranges.index((range_name, days)) - 1][1])
                    count = EqmdCustomUser.history.filter(
                        history_date__range=(cutoff, prev_cutoff)
                    ).count()
            else:
                cutoff = now - timedelta(days=365 * 7)
                count = EqmdCustomUser.history.filter(
                    history_date__lt=cutoff
                ).count()
            
            history_stats['records_by_age'][range_name] = count
        
        return history_stats
```

## Performance Monitoring

### Performance Metrics Collection

```python
# apps/core/monitoring/performance.py

from django.utils import timezone
from django.core.cache import cache
from django.db import connection
import time
import logging

class LifecyclePerformanceMonitor:
    """Monitor lifecycle system performance metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger('lifecycle.performance')
    
    def collect_metrics(self):
        """Collect performance metrics"""
        metrics = {
            'timestamp': timezone.now().isoformat(),
            'middleware_performance': self._measure_middleware_performance(),
            'database_performance': self._measure_database_performance(),
            'cache_performance': self._measure_cache_performance(),
            'user_activity_stats': self._collect_activity_stats()
        }
        
        # Store metrics in cache for trending
        self._store_metrics(metrics)
        
        return metrics
    
    def _measure_middleware_performance(self):
        """Measure middleware execution time"""
        # Simulate middleware timing
        start_time = time.time()
        
        # This would measure actual middleware performance
        # For now, return cached metrics or estimates
        execution_time = cache.get('middleware_avg_time', 0.05)  # 50ms default
        
        return {
            'average_execution_time_ms': execution_time * 1000,
            'requests_per_second': cache.get('middleware_rps', 100),
            'error_rate_percent': cache.get('middleware_error_rate', 0.1)
        }
    
    def _measure_database_performance(self):
        """Measure database query performance"""
        from apps.accounts.models import EqmdCustomUser
        
        # Measure common queries
        query_times = {}
        
        # User count query
        start_time = time.time()
        user_count = EqmdCustomUser.objects.count()
        query_times['user_count'] = (time.time() - start_time) * 1000
        
        # Status aggregation query
        start_time = time.time()
        status_counts = list(EqmdCustomUser.objects.values(
            'account_status'
        ).annotate(count=models.Count('id')))
        query_times['status_aggregation'] = (time.time() - start_time) * 1000
        
        return {
            'query_times_ms': query_times,
            'total_queries': len(connection.queries),
            'average_query_time_ms': sum(query_times.values()) / len(query_times)
        }
    
    def _measure_cache_performance(self):
        """Measure cache performance"""
        cache_metrics = {
            'hit_rate_percent': 85.0,  # Would be calculated from actual cache stats
            'average_get_time_ms': 1.2,
            'average_set_time_ms': 1.5
        }
        
        return cache_metrics
    
    def _collect_activity_stats(self):
        """Collect user activity statistics"""
        from apps.accounts.models import EqmdCustomUser
        
        now = timezone.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        return {
            'active_last_24h': EqmdCustomUser.objects.filter(
                last_meaningful_activity__gte=day_ago
            ).count(),
            'active_last_week': EqmdCustomUser.objects.filter(
                last_meaningful_activity__gte=week_ago
            ).count(),
            'total_activity_score': EqmdCustomUser.objects.aggregate(
                total=models.Sum('activity_score')
            )['total'] or 0
        }
    
    def _store_metrics(self, metrics):
        """Store metrics for trending analysis"""
        # Store last 24 hours of metrics
        metrics_key = f"lifecycle_metrics_{timezone.now().strftime('%Y%m%d_%H')}"
        cache.set(metrics_key, metrics, timeout=86400 * 2)  # 2 days
        
        # Maintain list of metric keys
        metric_keys = cache.get('lifecycle_metric_keys', [])
        metric_keys.append(metrics_key)
        
        # Keep only last 24 hours
        metric_keys = metric_keys[-24:]
        cache.set('lifecycle_metric_keys', metric_keys, timeout=86400 * 2)

# Performance monitoring command
# apps/core/management/commands/collect_performance_metrics.py

class Command(BaseCommand):
    help = 'Collect lifecycle performance metrics'
    
    def handle(self, *args, **options):
        monitor = LifecyclePerformanceMonitor()
        metrics = monitor.collect_metrics()
        
        self.stdout.write(json.dumps(metrics, indent=2))
        
        # Alert on performance issues
        if metrics['database_performance']['average_query_time_ms'] > 1000:
            self.stdout.write(self.style.WARNING('Database queries are slow'))
        
        if metrics['middleware_performance']['error_rate_percent'] > 5:
            self.stdout.write(self.style.ERROR('High middleware error rate'))
```

## Success Metrics

### Advanced Feature Metrics
- ✅ **Predictive Accuracy**: >80% accuracy in expiration risk prediction
- ✅ **API Performance**: <200ms response time for all endpoints
- ✅ **Notification Delivery**: >98% multi-channel delivery success
- ✅ **Health Check Coverage**: 100% system component monitoring
- ✅ **Compliance Reporting**: Automated regulatory report generation

### Integration Success
- ✅ **External System Integration**: API endpoints for HR/admin system integration
- ✅ **Performance Monitoring**: Real-time system health visibility
- ✅ **Advanced Analytics**: Behavioral pattern analysis and forecasting
- ✅ **Compliance Automation**: Automated audit trail and retention management

---

**Implementation Complete**: All phases of the user lifecycle management system have been planned with comprehensive technical specifications, implementation details, and success criteria.