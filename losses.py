import tensorflow as tf
import utils


def focal_sigmoid_cross_entropy_with_logits(labels, logits, focus=2.0, alpha=0.25,
                                            name='focal_sigmoid_cross_entropy_with_logits'):
    with tf.name_scope(name):
        alpha = tf.ones_like(labels) * alpha
        labels_eq_1 = tf.equal(labels, 1)

        loss = tf.nn.sigmoid_cross_entropy_with_logits(labels=labels, logits=logits)
        prob = tf.nn.sigmoid(logits)
        a_balance = tf.where(labels_eq_1, alpha, 1 - alpha)
        prob_true = tf.where(labels_eq_1, prob, 1 - prob)
        modulating_factor = (1.0 - prob_true)**focus

        return a_balance * modulating_factor * loss


# TODO: check if this is correct
def focal_softmax_cross_entropy_with_logits(labels, logits, focus=2.0, alpha=0.25, eps=1e-7,
                                            name='focal_softmax_cross_entropy_with_logits'):
    with tf.name_scope(name):
        alpha = tf.ones_like(labels) * alpha

        prob = tf.nn.softmax(logits, -1)

        labels_eq_1 = tf.equal(labels, 1)
        a_balance = tf.where(labels_eq_1, alpha, 1 - alpha)
        prob_true = tf.where(labels_eq_1, prob, 1 - prob)
        modulating_factor = (1.0 - prob_true)**focus

        log_prob = tf.log(prob + eps)
        loss = -tf.reduce_sum(a_balance * modulating_factor * labels * log_prob, -1)

        return loss


# def classification_loss(labels, logits, non_background_mask):
#     num_non_background = tf.reduce_sum(tf.to_float(non_background_mask))
#     class_loss = focal_sigmoid_cross_entropy_with_logits(labels=labels, logits=logits, focus=5.0)  # FIXME:
#     class_loss = tf.reduce_sum(class_loss) / tf.maximum(num_non_background, 1.0)
#
#     [logits_grad] = tf.gradients(class_loss, [logits])
#     logits_grad_fg = tf.boolean_mask(tf.abs(logits_grad), non_background_mask)
#     logits_grad_bg = tf.boolean_mask(tf.abs(logits_grad), tf.logical_not(non_background_mask))
#
#     tf.add_to_collection('logits_grad_fg', tf.reduce_sum(logits_grad_fg))
#     tf.add_to_collection('logits_grad_bg', tf.reduce_sum(logits_grad_bg))
#
#     return class_loss


# def classification_loss(labels, logits, non_background_mask, smooth=100):
#     prob = tf.nn.sigmoid(logits)
#
#     intersection = tf.reduce_sum(labels * prob, -1)
#     union = tf.reduce_sum(labels + prob, -1)
#     class_loss = (intersection + smooth) / (union - intersection + smooth)
#     class_loss = (1 - class_loss) * smooth
#     class_loss = tf.reduce_mean(class_loss)
#
#     [logits_grad] = tf.gradients(class_loss, [logits])
#     logits_grad_fg = tf.boolean_mask(logits_grad, non_background_mask)
#     logits_grad_bg = tf.boolean_mask(logits_grad, tf.logical_not(non_background_mask))
#
#     tf.add_to_collection('logits_grad_fg', logits_grad_fg)
#     tf.add_to_collection('logits_grad_bg', logits_grad_bg)
#
#     return class_loss

def classification_loss(labels, logits, non_background_mask, smooth=100):
    prob = tf.nn.sigmoid(logits)

    intersection = tf.reduce_sum(labels * prob)
    union = tf.reduce_sum(labels + prob)
    class_loss = (intersection + smooth) / (union - intersection + smooth)
    class_loss = (1 - class_loss) * smooth

    [logits_grad] = tf.gradients(class_loss, [logits])
    logits_grad_fg = tf.boolean_mask(logits_grad, non_background_mask)
    logits_grad_bg = tf.boolean_mask(logits_grad, tf.logical_not(non_background_mask))

    tf.add_to_collection('logits_grad_fg', logits_grad_fg)
    tf.add_to_collection('logits_grad_bg', logits_grad_bg)

    return class_loss


def regression_loss(labels, logits, non_background_mask):
    regr_loss = tf.losses.huber_loss(
        labels=labels,
        predictions=logits,
        weights=tf.expand_dims(non_background_mask, -1),
        reduction=tf.losses.Reduction.SUM_BY_NONZERO_WEIGHTS)

    check = tf.Assert(tf.is_finite(regr_loss), [tf.reduce_mean(regr_loss)])
    with tf.control_dependencies([check]):
        regr_loss = tf.identity(regr_loss)

    return regr_loss


def loss(labels, logits, not_ignored_masks, name='loss'):
    with tf.name_scope(name):
        labels = tuple(utils.merge_outputs(x, not_ignored_masks) for x in labels)
        logits = tuple(utils.merge_outputs(x, not_ignored_masks) for x in logits)

        class_labels, regr_labels = labels
        class_logits, regr_logits = logits

        non_background_mask = tf.not_equal(utils.classmap_decode(class_labels), -1)

        class_loss = classification_loss(
            labels=class_labels,
            logits=class_logits,
            non_background_mask=non_background_mask)
        regr_loss = regression_loss(
            labels=regr_labels,
            logits=regr_logits,
            non_background_mask=non_background_mask)

        return class_loss, regr_loss
