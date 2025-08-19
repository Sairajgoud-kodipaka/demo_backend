from apps.notifications.models import Notification
from apps.users.models import User

class StockTransferNotificationService:
    @staticmethod
    def notify_transfer_request(transfer):
        """Notify when a transfer is requested"""
        users_to_notify = []
        
        # Notify business admin
        business_admins = User.objects.filter(
            tenant=transfer.from_store.tenant,
            role='business_admin'
        )
        users_to_notify.extend(business_admins)
        
        # Notify receiving store manager
        receiving_store_managers = User.objects.filter(
            tenant=transfer.from_store.tenant,
            role='manager',
            store=transfer.to_store
        )
        users_to_notify.extend(receiving_store_managers)
        
        # Remove duplicates
        unique_users = list({user.id: user for user in users_to_notify}.values())
        
        for user in unique_users:
            Notification.objects.create(
                user=user,
                tenant=transfer.from_store.tenant,
                store=transfer.to_store,
                type='stock_transfer_request',
                title='New Stock Transfer Request',
                message=f'Transfer request for {transfer.quantity} units of {transfer.product.name} from {transfer.from_store.name} to {transfer.to_store.name}',
                priority='medium',
                action_url=f'/products/transfers/{transfer.id}',
                action_text='Review Transfer'
            )
    
    @staticmethod
    def notify_transfer_approved(transfer):
        """Notify when a transfer is approved"""
        users_to_notify = []
        
        # Notify requesting user
        users_to_notify.append(transfer.requested_by)
        
        # Notify business admin
        business_admins = User.objects.filter(
            tenant=transfer.from_store.tenant,
            role='business_admin'
        )
        users_to_notify.extend(business_admins)
        
        # Notify sending store manager
        sending_store_managers = User.objects.filter(
            tenant=transfer.from_store.tenant,
            role='manager',
            store=transfer.from_store
        )
        users_to_notify.extend(sending_store_managers)
        
        # Remove duplicates
        unique_users = list({user.id: user for user in users_to_notify}.values())
        
        for user in unique_users:
            Notification.objects.create(
                user=user,
                tenant=transfer.from_store.tenant,
                store=transfer.from_store,
                type='stock_transfer_approved',
                title='Stock Transfer Approved',
                message=f'Transfer of {transfer.quantity} units of {transfer.product.name} from {transfer.from_store.name} to {transfer.to_store.name} has been approved',
                priority='medium',
                action_url=f'/products/transfers/{transfer.id}',
                action_text='Complete Transfer'
            )
    
    @staticmethod
    def notify_transfer_completed(transfer):
        """Notify when a transfer is completed"""
        users_to_notify = []
        
        # Notify requesting user
        users_to_notify.append(transfer.requested_by)
        
        # Notify approving user
        if transfer.approved_by:
            users_to_notify.append(transfer.approved_by)
        
        # Notify business admin
        business_admins = User.objects.filter(
            tenant=transfer.from_store.tenant,
            role='business_admin'
        )
        users_to_notify.extend(business_admins)
        
        # Notify both store managers
        store_managers = User.objects.filter(
            tenant=transfer.from_store.tenant,
            role='manager',
            store__in=[transfer.from_store, transfer.to_store]
        )
        users_to_notify.extend(store_managers)
        
        # Remove duplicates
        unique_users = list({user.id: user for user in users_to_notify}.values())
        
        for user in unique_users:
            Notification.objects.create(
                user=user,
                tenant=transfer.from_store.tenant,
                store=transfer.to_store,
                type='stock_transfer_completed',
                title='Stock Transfer Completed',
                message=f'Transfer of {transfer.quantity} units of {transfer.product.name} from {transfer.from_store.name} to {transfer.to_store.name} has been completed successfully',
                priority='low',
                action_url=f'/products/transfers/{transfer.id}',
                action_text='View Details'
            )
    
    @staticmethod
    def notify_transfer_cancelled(transfer):
        """Notify when a transfer is cancelled"""
        users_to_notify = []
        
        # Notify requesting user
        users_to_notify.append(transfer.requested_by)
        
        # Notify business admin
        business_admins = User.objects.filter(
            tenant=transfer.from_store.tenant,
            role='business_admin'
        )
        users_to_notify.extend(business_admins)
        
        # Notify both store managers
        store_managers = User.objects.filter(
            tenant=transfer.from_store.tenant,
            role='manager',
            store__in=[transfer.from_store, transfer.to_store]
        )
        users_to_notify.extend(store_managers)
        
        # Remove duplicates
        unique_users = list({user.id: user for user in users_to_notify}.values())
        
        for user in unique_users:
            Notification.objects.create(
                user=user,
                tenant=transfer.from_store.tenant,
                store=transfer.from_store,
                type='stock_transfer_cancelled',
                title='Stock Transfer Cancelled',
                message=f'Transfer of {transfer.quantity} units of {transfer.product.name} from {transfer.from_store.name} to {transfer.to_store.name} has been cancelled',
                priority='medium',
                action_url=f'/products/transfers/{transfer.id}',
                action_text='View Details'
            )
