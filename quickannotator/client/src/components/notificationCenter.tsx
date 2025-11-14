import { useState } from "react";
import Offcanvas from 'react-bootstrap/Offcanvas';
import Button from 'react-bootstrap/Button';
import ListGroup from 'react-bootstrap/ListGroup';
import Badge from 'react-bootstrap/Badge';

type Props = {
  show: boolean;
  onHide: () => void;
  // pass in the object returned from the useNotificationCenter() hook
  notificationCenter: any;
};

export default function NotificationCenter({ show, onHide, notificationCenter }: Props) {
  // Use the passed-in notificationCenter instead of calling the hook here.
  const { notifications = [], clear, markAllAsRead, markAsRead, remove, unreadCount } = notificationCenter || {};
  const [showUnreadOnly, setShowUnreadOnly] = useState(true);

  const list = showUnreadOnly ? (notifications || []).filter((n: any) => !n.read) : (notifications || []);

  return (
    <Offcanvas show={show} onHide={onHide} placement="end">
      <Offcanvas.Header closeButton>
        <Offcanvas.Title>
          Notifications{' '}
          <Badge bg="secondary">{unreadCount || 0}</Badge>
        </Offcanvas.Title>
      </Offcanvas.Header>
      <Offcanvas.Body>
        <div className="d-flex justify-content-between align-items-center mb-2">
          <div>
            <input
              id="unread-filter"
              type="checkbox"
              checked={showUnreadOnly}
              onChange={() => setShowUnreadOnly((v) => !v)}
            />{' '}
            <label htmlFor="unread-filter">Only show unread</label>
          </div>
          <div>
            <Button variant="outline-secondary" size="sm" onClick={markAllAsRead} className="me-2">Mark all read</Button>
            <Button variant="outline-danger" size="sm" onClick={clear}>Clear</Button>
          </div>
        </div>

        {!list || list.length === 0 ? (
          <div className="text-center text-muted">Your queue is empty!</div>
        ) : (
          <ListGroup>
            {list.map((n: any) => (
              <ListGroup.Item key={n.id} className="d-flex justify-content-between align-items-start">
                <div>
                  <div style={{ fontWeight: n.read ? 'normal' : '600' }}>{n.content}</div>
                  {n.createdAt && (
                    <div className="text-muted small">{new Date(n.createdAt).toLocaleString()}</div>
                  )}
                </div>
                <div className="d-flex flex-column align-items-end">
                  {!n.read && (
                    <Button variant="link" size="sm" onClick={() => markAsRead(n.id)}>Mark read</Button>
                  )}
                  <Button variant="link" size="sm" onClick={() => remove(n.id)}>Dismiss</Button>
                </div>
              </ListGroup.Item>
            ))}
          </ListGroup>
        )}
      </Offcanvas.Body>
    </Offcanvas>
  );
}
