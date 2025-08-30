"""
Simplified service for basic user activity tracking
"""


class SimpleUserActivityTracker:
    """Simplified service for basic user activity tracking"""
    
    @classmethod
    def track_activity(cls, user):
        """Track any meaningful user activity (simplified)"""
        user.update_activity_timestamp()
    
    @classmethod
    def track_patient_access(cls, user, patient):
        """Track patient-related activities"""
        cls.track_activity(user)
    
    @classmethod
    def track_note_creation(cls, user):
        """Track medical note creation"""
        cls.track_activity(user)
    
    @classmethod
    def track_form_completion(cls, user):
        """Track PDF form completions"""
        cls.track_activity(user)